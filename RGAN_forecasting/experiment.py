import numpy as np
import tensorflow as tf
import pdb
import random
import json
from scipy.stats import mode

import data_utils
import plotting
import model
import utils
import eval

from time import time
from math import floor
from mmd import rbf_mmd2, median_pairwise_distance, mix_rbf_mmd2_and_ratio
import mmd
import pandas as pd

tf.logging.set_verbosity(tf.logging.ERROR)

# --- get settings --- #
# parse command line arguments, or use defaults
parser = utils.rgan_options_parser()
settings = vars(parser.parse_args())
# if a settings file is specified, it overrides command line arguments/defaults
if settings['settings_file']: settings = utils.load_settings_from_file(settings)

# --- get data, split --- #
samples, pdf, labels = data_utils.get_samples_and_labels(settings)

# --- save settings, data --- #
print('Ready to run with settings:')
for (k, v) in settings.items(): print(v, '\t',  k)
# add the settings to local environment
# WARNING: at this point a lot of variables appear
locals().update(settings)
json.dump(settings, open('./experiments/settings/' + identifier + '.txt', 'w'), indent=0)
epoch = 150

#if not data == 'load':
#    data_path = './experiments/data/' + identifier + '.data.npy'
#    np.save(data_path, {'samples': samples, 'pdf': pdf, 'labels': labels})
#    print('Saved training data to', data_path)

# --- build model --- #

Z, X, CG, CD, CS = model.create_placeholders(batch_size, seq_length, latent_dim, num_generated_features, cond_dim)

discriminator_vars = ['hidden_units_d', 'seq_length', 'cond_dim', 'batch_size', 'batch_mean', 'latent_dim']
discriminator_settings = dict((k, settings[k]) for k in discriminator_vars)
generator_vars = ['hidden_units_g', 'seq_length', 'batch_size', 'latent_dim', 
                  'num_generated_features', 'cond_dim', 'learn_scale']
generator_settings = dict((k, settings[k]) for k in generator_vars)

CGAN = (cond_dim > 0)
if CGAN: assert not predict_labels

#D_loss, G_loss, D_logit_real, D_logit_fake = model.GAN_loss(Z, X, generator_settings, discriminator_settings,
D_loss, G_loss = model.GAN_loss(Z, X, generator_settings, discriminator_settings,
        kappa, CGAN, CG, CD, CS, wrong_labels=wrong_labels)
D_solver, G_solver, priv_accountant = model.GAN_solvers(D_loss, G_loss, learning_rate, batch_size, 
        total_examples=samples['train'].shape[0], l2norm_bound=l2norm_bound,
        batches_per_lot=batches_per_lot, sigma=dp_sigma, dp=dp)
G_sample = model.generator(Z, **generator_settings, reuse=True, c=CG)

saver = tf.train.Saver()

# --- evaluation --- #

# frequency to do visualisations
vis_freq = max(14000//num_samples, 1)
eval_freq = max(7000//num_samples, 1)
eval_freq=1

# get heuristic bandwidth for mmd kernel from evaluation samples
heuristic_sigma_training = median_pairwise_distance(samples['vali'])
# best_mmd2_so_far = 1000
best_rmse_so_far = 1000000

# optimise sigma using that (that's t-hat)
batch_multiplier = 5000//batch_size
eval_size = batch_multiplier*batch_size
eval_eval_size = int(0.2*eval_size)
eval_real_PH = tf.placeholder(tf.float32, [eval_eval_size, 1, num_generated_features])
eval_sample_PH = tf.placeholder(tf.float32, [eval_eval_size, 1, num_generated_features])
n_sigmas = 2
sigma = tf.get_variable(name='sigma', shape=n_sigmas, initializer=tf.constant_initializer(value=np.power(heuristic_sigma_training, np.linspace(-1, latent_dim, num=n_sigmas))))
# mmd2, that = mix_rbf_mmd2_and_ratio(eval_real_PH, eval_sample_PH, sigma)
rmse = None #tf.reduce_mean(tf.reduce_sum((eval_real_PH - eval_sample_PH)**2))

# with tf.variable_scope("SIGMA_optimizer"):
#     sigma_solver = tf.train.RMSPropOptimizer(learning_rate=0.05).minimize(-that, var_list=[sigma])
    #sigma_solver = tf.train.AdamOptimizer().minimize(-that, var_list=[sigma])
    #sigma_solver = tf.train.AdagradOptimizer(learning_rate=0.1).minimize(-that, var_list=[sigma])
sigma_opt_iter = 2000
sigma_opt_thresh = 0.001
sigma_opt_vars = [var for var in tf.global_variables() if 'SIGMA_optimizer' in var.name]

sess = tf.Session()
sess.run(tf.global_variables_initializer())

# for dp
target_eps = [0.125, 0.25, 0.5, 1, 2, 4, 8]
#dp_trace = open('./experiments/traces/' + identifier + '.dptrace.txt', 'w')
#dp_trace.write('epoch ' + ' eps' .join(map(str, target_eps)) + '\n')

#trace = open('./experiments/traces/' + identifier + '.trace.txt', 'w')
#trace.write('epoch time D_loss G_loss mmd2 that pdf real_pdf\n')

# --- train --- #
train_vars = ['batch_size', 'D_rounds', 'G_rounds', 'use_time', 'seq_length', 'latent_dim',
              'num_generated_features', 'cond_dim', 'max_val',
              'WGAN_clip', 'one_hot']
train_settings = dict((k, settings[k]) for k in train_vars)


t0 = time()
best_epoch = 0
print('epoch\ttime\tD_loss\tG_loss\tmmd2\tpdf_sample\tpdf_real')
mmd_calc = None
kernel_calc = None
for epoch in range(num_epochs):
    D_loss_curr, G_loss_curr = model.train_epoch(epoch, samples['train'], labels['train'],
                                        sess, Z, X, CG, CD, CS,
                                        D_loss, G_loss,
                                        #D_logit_real, D_logit_fake,
                                        #conv, layer, w,
                                        D_solver, G_solver,
                                        **train_settings)
   
    # compute mmd2 and, if available, prob density
    if epoch % eval_freq == 0:
        ## how many samples to evaluate with?
        validation = np.float32(samples['vali'][np.random.choice(len(samples['vali']), size=batch_multiplier*batch_size), :, :])
        eval_Z = validation[:, :-latent_dim, :]#model.sample_Z(eval_size, seq_length, use_time)
        if 'eICU_task' in data:
            eval_C = labels['vali'][np.random.choice(labels['vali'].shape[0], eval_size), :]
        else:
            eval_C = model.sample_C(eval_size, cond_dim, max_val, one_hot)
        eval_sample = np.empty(shape=(eval_size, latent_dim, num_signals))
        for i in range(batch_multiplier):
            if CGAN:
                eval_sample[i*batch_size:(i+1)*batch_size, :, :] = sess.run(G_sample, feed_dict={Z: eval_Z[i*batch_size:(i+1)*batch_size], CG: eval_C[i*batch_size:(i+1)*batch_size]})
            else:
                eval_sample[i*batch_size:(i+1)*batch_size, :, :] = sess.run(G_sample, feed_dict={Z: eval_Z[i*batch_size:(i+1)*batch_size]})
        eval_sample = np.float32(eval_sample)
        eval_real = validation[:, -latent_dim:, :]
       
        eval_eval_real = eval_real[:eval_eval_size].reshape(-1, latent_dim, num_generated_features)
        eval_test_real = eval_real[eval_eval_size:].reshape(-1, latent_dim, num_generated_features)
        eval_eval_sample = eval_sample[:eval_eval_size].reshape(-1, latent_dim, num_generated_features)
        eval_test_sample = eval_sample[eval_eval_size:].reshape(-1, latent_dim, num_generated_features)
        
        ## MMD
        # reset ADAM variables
        sess.run(tf.initialize_variables(sigma_opt_vars))
        sigma_iter = 0
        # that_change = sigma_opt_thresh*2
        # old_that = 0
        #while that_change > sigma_opt_thresh and sigma_iter < sigma_opt_iter:
        #    sess.run(sigma_solver, feed_dict={eval_real_PH: eval_eval_real, eval_sample_PH: eval_eval_sample})
        #    sess.run(sigma)
        #    that_np = sess.run(that, feed_dict={eval_real_PH: eval_eval_real, eval_sample_PH: eval_eval_sample})
        #    that_change = np.abs(that_np - old_that)
        #    old_that = that_np
        #    sigma_iter += 1
        #opt_sigma = sess.run(sigma)
        if epoch == 0:
            eval_test_real_PH = tf.placeholder(tf.float32, eval_test_real.shape)
            eval_test_sample_PH = tf.placeholder(tf.float32, eval_test_sample.shape)
            # kernel_calc = mmd._mix_rbf_kernel(eval_test_real_PH, eval_test_sample_PH, sigma, None)
            # mmd_calc = mix_rbf_mmd2_and_ratio(eval_test_real_PH, eval_test_sample_PH, biased=False, sigmas=sigma)
            rmse_ind_mean = tf.reduce_mean((eval_test_real_PH - eval_test_sample_PH)**2, 2)**0.5
            rmse_calc = tf.reduce_mean(tf.reduce_mean(rmse_ind_mean, 1))
        #mmd2, that_np = sess.run(mix_rbf_mmd2_and_ratio(eval_test_real, eval_test_sample,biased=False, sigmas=sigma))
        # mmd2, that_np = sess.run(mmd_calc, feed_dict={eval_test_real_PH: eval_test_real, eval_test_sample_PH: eval_test_sample})
        rmse = sess.run(rmse_calc, feed_dict={eval_test_real_PH: eval_test_real, eval_test_sample_PH: eval_test_sample})

        ## save parameters
        # if mmd2 < best_mmd2_so_far and epoch > 10:
        if rmse < best_rmse_so_far and epoch > 10:
            best_epoch = epoch
            # best_mmd2_so_far = mmd2
            best_rmse_so_far = rmse
            #model.dump_parameters(identifier + '_' + str(epoch), sess)
            save_path = saver.save(sess, 'experiments/parameters/krishna_dance_params/krishna_dance_{}.ckpt'.format(epoch))
            print('Model parameters saved at: {}'.format(save_path))
       
        ## prob density (if available)
        if not pdf is None:
            pdf_sample = np.mean(pdf(eval_sample[:, :, 0]))
            pdf_real = np.mean(pdf(eval_real[:, :, 0]))
        else:
            pdf_sample = 'NA'
            pdf_real = 'NA'
    else:
        # report nothing this epoch
        # mmd2 = 'NA'
        rmse = 'NA'
        that = 'NA'
        pdf_sample = 'NA'
        pdf_real = 'NA'

    t = time() - t0
    try:
        # print('%d\t%.2f\t%.4f\t%.4f\t%.5f\t%.2f\t%.2f' % (epoch, t, D_loss_curr, G_loss_curr, mmd2, pdf_sample, pdf_real))
        print('%d\t%.2f\t%.4f\t%.4f\t%.5f\t%.2f\t%.2f' % (epoch, t, D_loss_curr, G_loss_curr, rmse, pdf_sample, pdf_real))
    except TypeError:       # pdf are missing (format as strings)
        # print('%d\t%.2f\t%.4f\t%.4f\t%.5f\t %s\t %s' % (epoch, t, D_loss_curr, G_loss_curr, mmd2, pdf_sample, pdf_real))
        print('%d\t%.2f\t%.4f\t%.4f\t%.5f\t %s\t %s' % (epoch, t, D_loss_curr, G_loss_curr, rmse, pdf_sample, pdf_real))

    if shuffle:     # shuffle the training data 
        perm = np.random.permutation(samples['train'].shape[0])
        samples['train'] = samples['train'][perm]
        if labels['train'] is not None:
            labels['train'] = labels['train'][perm]
    
    if epoch % 50 == 0:
        save_path = saver.save(sess, 'experiments/parameters/krishna_dance_params/krishna_dance_{}.ckpt'.format(epoch))
        print('Model parameters saved at: {}'.format(save_path))

save_path = saver.save(sess, 'experiments/parameters/krishna_dance_params/krishna_dance_{}.ckpt'.format(epoch))
print('Model parameters saved at: {}'.format(save_path))