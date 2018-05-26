import tensorflow as tf
import numpy as np
#from data_utils import get_batch
import time

import data_utils
import pdb
import json
from mod_core_rnn_cell_impl import LSTMCell, DropoutWrapper  # modified to allow initializing bias in lstm
#from tensorflow.contrib.rnn import LSTMCell
tf.logging.set_verbosity(tf.logging.ERROR)
import mmd

from differential_privacy.dp_sgd.dp_optimizer import dp_optimizer
from differential_privacy.dp_sgd.dp_optimizer import sanitizer
from differential_privacy.privacy_accountant.tf import accountant

# --- to do with latent space --- #

noise_file = 'Z_mb.csv'
input_file = 'X_mb.csv'

columns = [str(i) for i in range(1, 15)]
columns_noise = [str(i) for i in range(1, 4)]


def sample_Z(batch_size, seq_length, latent_dim, num_generated_features, data, use_time=False, use_noisy_time=False):
    sample = np.float32(data[batch_size]).reshape(-1, seq_length-latent_dim, num_generated_features)
    return sample

def sample_C(batch_size, cond_dim=0, max_val=1, one_hot=False):
    """
    return an array of integers (so far we only allow integer-valued
    conditional values)
    """
    if cond_dim == 0:
        return None
    else:
        if one_hot:
            assert max_val == 1
            C = np.zeros(shape=(batch_size, cond_dim))
            # locations
            labels = np.random.choice(cond_dim, batch_size)
            C[np.arange(batch_size), labels] = 1
        else:
            C = np.random.choice(max_val+1, size=(batch_size, cond_dim))
        return C

# --- to do with training --- #
def store_to_file(X, Z):
    import os
    import pandas as pd
    X_dims = X.shape
    Z_dims = Z.shape
    X_val = X[0, :, :]
    Z_val = Z[0, :, :]
    for i in range(1, X_dims[0]):
        X_val = np.append(X_val, np.zeros((1, X_dims[2])),axis=0)
        X_val = np.append(X_val, X[i, :, :], axis=0)
    for i in range(1, Z_dims[0]):
        Z_val = np.append(Z_val, np.zeros((1, Z_dims[2])),axis=0)
        Z_val = np.append(Z_val, Z[i, :, :], axis=0)
    X_df = pd.DataFrame(X_val, columns=columns)
    Z_df = pd.DataFrame(Z_val, columns=columns_noise)
    if not os.path.exists(input_file):
        X_df.to_csv(input_file, index=None)
    else:
        output_X = pd.DataFrame(np.zeros((1, X_val.shape[1])), columns=columns)
        output_X = pd.read_csv(input_file).append(output_X, ignore_index=True)
        output_X = output_X.append(X_df, ignore_index=True)
        output_X.to_csv(input_file, index=None)
    if not os.path.exists(noise_file):
        Z_df.to_csv(noise_file, index=None)
    else:
        output_Z = pd.DataFrame(np.zeros((1, Z_val.shape[1])), columns=columns_noise)
        output_Z = pd.read_csv(noise_file).append(output_Z, ignore_index=True)
        output_Z = output_Z.append(Z_df, ignore_index=True)
        output_Z.to_csv(noise_file, index=None)

def train_epoch(epoch, samples, labels, sess, Z, X, CG, CD, CS, D_loss, G_loss, #D_logit_real, D_logit_fake, conv1,
                D_solver, G_solver, batch_size, use_time, D_rounds, G_rounds, seq_length, latent_dim,
                #layer, w, D_solver, G_solver, batch_size, use_time, D_rounds, G_rounds, seq_length,
                num_generated_features, cond_dim, max_val, WGAN_clip, one_hot):
    """
    Train generator and discriminator for one epoch.
    """
    for batch_idx in range(0, int(len(samples) / batch_size) - (D_rounds + (cond_dim > 0)*G_rounds), D_rounds + (cond_dim > 0)*G_rounds):
        # update the discriminator
        for d in range(D_rounds):
            X_mb, Y_mb = data_utils.get_batch(samples, batch_size, batch_idx + d, labels)
            Z_mb = X_mb[:, :-latent_dim, :] #sample_Z(batch_size, seq_length, latent_dim, use_time)
            X_mb = X_mb[:, -latent_dim:, :]
            X_mb = X_mb.reshape(-1, latent_dim, num_generated_features)
            if cond_dim > 0:
                # CGAN
                Y_mb = Y_mb.reshape(-1, cond_dim)
                if one_hot:
                    # change all of the labels to a different one
                    offsets = np.random.choice(cond_dim-1, batch_size) + 1
                    new_labels = (np.argmax(Y_mb, axis=1) + offsets) % cond_dim
                    Y_wrong = np.zeros_like(Y_mb)
                    Y_wrong[np.arange(batch_size), new_labels] = 1
                else:
                    # flip all of the bits (assuming binary...)
                    Y_wrong = 1 - Y_mb
                _ = sess.run(D_solver, feed_dict={X: X_mb, Z: Z_mb, CD: Y_mb, CS: Y_wrong, CG: Y_mb})
            else:
                _ = sess.run(D_solver, feed_dict={X: X_mb, Z: Z_mb})
            if WGAN_clip:
                raise NotImplementedError("Not implemented WGAN")
                # clip the weights
                # _ = sess.run([clip_disc_weights])
        # update the generator
        for g in range(G_rounds):
            if cond_dim > 0:
                # note we are essentially throwing these X_mb away...
                X_mb, Y_mb = data_utils.get_batch(samples, batch_size, batch_idx + D_rounds + g, labels)
                _ = sess.run(G_solver,
                        feed_dict={Z: sample_Z(batch_size, seq_length, latent_dim, use_time=use_time), CG: Y_mb})
            else:
                Z_mb, Y_mb = data_utils.get_batch(samples, batch_size, batch_idx, labels)
                Z_mb = Z_mb[:, :-latent_dim, :]
                _ = sess.run(G_solver,
                        feed_dict={Z: Z_mb})#sample_Z(batch_size, seq_length, use_time=use_time)})
    # at the end, get the loss
    if cond_dim > 0:
        D_loss_curr, G_loss_curr = sess.run([D_loss, G_loss], feed_dict={X: X_mb, Z: sample_Z(batch_size, seq_length, latent_dim, use_time=use_time), CG: Y_mb, CD: Y_mb})
        D_loss_curr = np.mean(D_loss_curr)
        G_loss_curr = np.mean(G_loss_curr)
    else:
        D_loss_curr, G_loss_curr =\
            sess.run([D_loss, G_loss], feed_dict={X: X_mb, Z: Z_mb})#sample_Z(batch_size, seq_length, use_time=use_time)})
        D_loss_curr = np.mean(D_loss_curr)
        G_loss_curr = np.mean(G_loss_curr)
    return D_loss_curr, G_loss_curr

def WGAN_loss(Z, X, WGAN_clip=False):
   
    raise NotImplementedError
    G_sample = generator(Z, hidden_units_g, W_out_G, b_out_G, scale_out_G)
    
    D_real, D_logit_real, D_logit_real_final = discriminator(X, hidden_units_d, seq_length, batch_size)
    
    D_loss = tf.reduce_mean(D_fake) - tf.reduce_mean(D_real)
    G_loss = -tf.reduce_mean(D_fake)

    if not WGAN_clip:
        # gradient penalty from improved WGAN code
        # ... but it doesn't work in TF for RNNs, so let's skip it for now
#        alpha = np.random.uniform(size=batch_size, low=0.0, high=1.0).reshape(batch_size, 1, 1)
#        interpolates = alpha*X + ((1-alpha)*G_sample)
#        pdb.set_trace()
#        disc_interpolates, _ = discriminator(interpolates, reuse=True)
#        gradients = tf.gradients(disc_interpolates, [interpolates])[0]
#        slopes = tf.sqrt(tf.reduce_sum(tf.square(gradients), reduction_indices=[1]))
#        gradient_penalty = tf.reduce_mean((slopes-1)**2)

        # now for my own hack
        # sample a random h
        h = tf.random_normal(shape=X.shape, stddev=0.1)
        D_offset, _ = discriminator(X + h, hidden_units_d)
        gradient_penalty = tf.norm(D_offset - D_real)

        KAPPA = 1.0
        D_loss += KAPPA*gradient_penalty
        
        clip_disc_weights = None
    else:
        # weight clipping from original WGAN
            # Build an op to do the weight clipping
        clip_ops = []
        for var in discriminator_vars:
            clip_bounds = [-.01, .01]
            clip_ops.append(
                tf.assign(
                    var,
                    tf.clip_by_value(var, clip_bounds[0], clip_bounds[1])
                )
            )
        clip_disc_weights = tf.group(*clip_ops)

    return G_loss, D_loss, clip_disc_weights

def GAN_loss(Z, X, generator_settings, discriminator_settings, kappa, cond, CG, CD, CS, wrong_labels=False):
    if cond:
        # C-GAN
        G_sample = generator(Z, **generator_settings, c=CG)
        D_real, _ =  discriminator(X, **discriminator_settings, c=CD)
        D_fake, _ = discriminator(G_sample, reuse=True, **discriminator_settings, c=CG)
        #D_real, D_logit_real =  discriminator(X, **discriminator_settings, c=CD)
        #D_fake, D_logit_fake = discriminator(G_sample, reuse=True, **discriminator_settings, c=CG)
        
        if wrong_labels:
            # the discriminator must distinguish between real data with fake labels and real data with real labels, too
            D_wrong, D_logit_wrong = discriminator(X, reuse=True, **discriminator_settings, c=CS)
    else:
        # normal GAN
        G_sample = generator(Z, **generator_settings)
        D_real, _ = discriminator(X, **discriminator_settings)
        D_fake, _ = discriminator(G_sample, reuse=True, **discriminator_settings)
        #D_real, D_logit_real = discriminator(X, **discriminator_settings)
        #D_fake, D_logit_fake = discriminator(G_sample, reuse=True, **discriminator_settings)

    # D_loss_real = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=D_logit_real, labels=tf.ones_like(D_logit_real)), 1)
    # D_loss_fake = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=D_logit_fake, labels=tf.zeros_like(D_logit_fake)), 1)
    #D_loss_real = tf.reduce_mean(tf.nn.l2_loss(D_logit_real - tf.ones_like(D_logit_real)), 1)
    #D_loss_fake = tf.reduce_mean(tf.nn.l2_loss(D_logit_fake - tf.zeros_like(D_logit_fake)), 1)
    D_loss_real = tf.reduce_mean((D_real - tf.ones_like(D_real)) * (D_real - tf.ones_like(D_real)), 1)
    D_loss_fake = tf.reduce_mean(D_fake * D_fake, 1)

    D_loss = (D_loss_real + D_loss_fake)/2

    if cond and wrong_labels:
        D_loss = D_loss + D_loss_wrong

    #G_loss = tf.reduce_mean(tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=D_logit_fake, labels=tf.ones_like(D_logit_fake)), axis=1))
    # G_loss = tf.reduce_mean(tf.nn.sigmoid_cross_entropy_with_logits(logits=D_logit_fake, labels=tf.ones_like(D_logit_fake)), 1)
    G_loss = (tf.reduce_mean((D_fake - tf.ones_like(D_fake)) * (D_fake - tf.ones_like(D_fake)), 1))/2
    
    return D_loss, G_loss #, D_logit_real, D_logit_fake

def GAN_solvers(D_loss, G_loss, learning_rate, batch_size, total_examples, 
        l2norm_bound, batches_per_lot, sigma, dp=False):
    """
    Optimizers
    """
    discriminator_vars = [v for v in tf.trainable_variables() if v.name.startswith('discriminator')]
    generator_vars = [v for v in tf.trainable_variables() if v.name.startswith('generator')]
    if dp:
        print('Using differentially private SGD to train discriminator!')
        eps = tf.placeholder(tf.float32)
        delta = tf.placeholder(tf.float32)
        priv_accountant = accountant.GaussianMomentsAccountant(total_examples)
        clip = True
        l2norm_bound = l2norm_bound/batch_size
        batches_per_lot = 1
        gaussian_sanitizer = sanitizer.AmortizedGaussianSanitizer(
                priv_accountant,
                [l2norm_bound, clip])
       
        # the trick is that we need to calculate the gradient with respect to
        # each example in the batch, during the DP SGD step
        D_solver = dp_optimizer.DPGradientDescentOptimizer(learning_rate,
                [eps, delta],
                sanitizer=gaussian_sanitizer,
                sigma=sigma,
                batches_per_lot=batches_per_lot).minimize(D_loss, var_list=discriminator_vars)
    else:
        D_loss_mean_over_batch = tf.reduce_mean(D_loss)
        D_solver = tf.train.GradientDescentOptimizer(learning_rate=learning_rate).minimize(D_loss_mean_over_batch, var_list=discriminator_vars)
        priv_accountant = None
    G_loss_mean_over_batch = tf.reduce_mean(G_loss)
    G_solver = tf.train.AdamOptimizer().minimize(G_loss_mean_over_batch, var_list=generator_vars)
    return D_solver, G_solver, priv_accountant

# --- to do with the model --- #

def create_placeholders(batch_size, seq_length, latent_dim, num_generated_features, cond_dim):
    Z = tf.placeholder(tf.float32, [batch_size, seq_length-latent_dim, num_generated_features], 'Z')
    X = tf.placeholder(tf.float32, [batch_size, latent_dim, num_generated_features], 'X')
    CG = tf.placeholder(tf.float32, [batch_size, cond_dim], 'CG')
    CD = tf.placeholder(tf.float32, [batch_size, cond_dim], 'CD')
    CS = tf.placeholder(tf.float32, [batch_size, cond_dim], 'CS')
    return Z, X, CG, CD, CS

def conv2d_layer(inputs, weight_shape, bias_shape, index, ksize, strides, pool_strides, padding='SAME'):
    w = tf.get_variable('w' + str(index), shape=weight_shape, initializer=tf.contrib.layers.xavier_initializer())
    b = tf.get_variable('b' + str(index), shape=bias_shape, initializer=tf.contrib.layers.xavier_initializer())
    conv_layer = tf.nn.conv2d(inputs, w, strides=strides, padding=padding, name='conv_'.format(index))
    relu = tf.nn.relu(conv_layer, 'relu_'.format(index))
    pool = tf.nn.max_pool(relu, ksize, pool_strides, padding=padding, name='pool_{}'.format(index))
    return pool

def generator(z, hidden_units_g, seq_length, batch_size, num_generated_features, latent_dim,
              reuse=False, parameters=None, cond_dim=0, c=None, learn_scale=True):
    """
    If parameters are supplied, initialise as such
    """
    with tf.variable_scope("generator") as scope:
        if reuse:
            scope.reuse_variables()

        ##
        if parameters is None:
            W_out_G_initializer = tf.truncated_normal_initializer()
            b_out_G_initializer = tf.truncated_normal_initializer()
            scale_out_G_initializer = tf.constant_initializer(value=1.0)
            lstm_initializer = None
            bias_start = 1.0
        else:
            W_out_G_initializer = tf.constant_initializer(value=parameters['generator/W_out_G:0'])
            b_out_G_initializer = tf.constant_initializer(value=parameters['generator/b_out_G:0'])
            try:
                scale_out_G_initializer = tf.constant_initializer(value=parameters['generator/scale_out_G:0'])
            except KeyError:
                scale_out_G_initializer = tf.constant_initializer(value=1)
                assert learn_scale
            lstm_initializer = tf.constant_initializer(value=parameters['generator/rnn/lstm_cell/weights:0'])
            bias_start = parameters['generator/rnn/lstm_cell/biases:0']

        W_out_G = tf.get_variable(name='W_out_G', shape=[hidden_units_g, 5], initializer=W_out_G_initializer)
        b_out_G = tf.get_variable(name='b_out_G', shape=5, initializer=b_out_G_initializer)
        scale_out_G = tf.get_variable(name='scale_out_G', shape=1, initializer=scale_out_G_initializer, trainable=learn_scale)
        if cond_dim > 0:
            # CGAN!
            assert not c is None
            repeated_encoding = tf.stack([c]*seq_length, axis=1)
            inputs = tf.concat([z, repeated_encoding], axis=2)

            #repeated_encoding = tf.tile(c, [1, tf.shape(z)[1]])
            #repeated_encoding = tf.reshape(repeated_encoding, [tf.shape(z)[0], tf.shape(z)[1], cond_dim])
            #inputs = tf.concat([repeated_encoding, z], 2)
        else:
            # inputs = z
            inputs = tf.reshape(z, [-1, 60, 75, 1])

        keep_prob=0.9

        ### First convolutional layer
        conv_1 = conv2d_layer(inputs, [5, 5, 1, 32], [32], 1, [1, 3, 3, 1], [1, 1, 1, 1], [1, 3, 3, 1], 'SAME')
        # drop1 = tf.nn.dropout(inputs, keep_prob)
        print("Generator conv1 output shape: {}".format(conv_1.shape))

        ### Second convolutional layern
        conv_2 = conv2d_layer(conv_1, [4, 4, 32, 64], [64], 2, [1, 2, 2, 1], [1, 1, 1, 1], [1, 2, 2, 1], 'SAME')
        # drop2 = tf.nn.dropout(conv_2, keep_prob)
        print("Generator conv2 output shape: {}".format(conv_2.shape))

        ### Third convolutional layer
        conv_3 = conv2d_layer(conv_2, [2, 2, 64, 64], [64], 3, [1, 2, 2, 1], [1, 1, 1, 1], [1, 2, 2, 1], 'SAME')
        # drop3 = tf.nn.dropout(conv_3, keep_prob)
        print("Generator conv3 output shape: {}".format(conv_3.shape))

        ### Fourth convolutional layer
        conv_4 = conv2d_layer(conv_3, [2, 2, 64, 128], [1], 4, [1, 2, 2, 1], [1, 1, 1, 1], [1, 2, 2, 1], 'SAME')
        # drop4 = tf.nn.dropout(conv_4, keep_prob)
        print("Generator conv4 output shape: {}".format(conv_4.shape))

        ### Fifth convolutional layer
        conv_5 = conv2d_layer(conv_4, [2, 2, 128, 1], [1], 5, [1, 2, 2, 1], [1, 1, 1, 1], [1, 2, 2, 1], 'SAME')
        print("Generator conv5 output shape: {}".format(conv_5.shape))

        cell = LSTMCell(num_units=hidden_units_g,
                        state_is_tuple=True,
                        initializer=lstm_initializer,
                        bias_start=bias_start,
                        reuse=reuse)

        rnn_outputs, rnn_states = tf.nn.dynamic_rnn(
            cell=cell,
            dtype=tf.float32,
            sequence_length=[seq_length - latent_dim]*batch_size,
            inputs=tf.reshape(conv_5, [-1, 2, 2]))

        rnn_outputs_2d = tf.reshape(rnn_outputs, [-1, hidden_units_g])
        logits_2d = tf.matmul(rnn_outputs_2d, W_out_G) + b_out_G
#        output_2d = tf.multiply(tf.nn.tanh(logits_2d), scale_out_G)
        output_2d = tf.nn.tanh(logits_2d)
        output_3d = tf.reshape(output_2d, [-1, 2, 5, 1])#num_generated_features])

        ## deconv1
        deconv1 = tf.nn.conv2d_transpose(output_3d, tf.get_variable('dw1', shape=[4, 4, 64, 1], initializer=tf.contrib.layers.xavier_initializer()),
                                         strides=[1, 3, 3, 1], output_shape=[28, 5, 13, 64], padding='SAME', name='deconv1')
        de_relu1 = tf.nn.relu(deconv1, 'de_relu1')


        ## deconv2
        deconv2 = tf.nn.conv2d_transpose(de_relu1, tf.get_variable('dw2', shape=[5, 5, 32, 64], initializer=tf.contrib.layers.xavier_initializer()),
                                         strides=[1, 2, 2, 1], output_shape=[28, 10, 25, 32], padding='SAME', name='deconv2')
        de_relu2 = tf.nn.relu(deconv2, 'de_relu2')

        ## deconv3
        deconv3 = tf.nn.conv2d_transpose(de_relu2, tf.get_variable('dw3', shape=[5, 5, 1, 32], initializer=tf.contrib.layers.xavier_initializer()),
                                         strides=[1, 2, 3, 1], output_shape=[28, 20, 75, 1], padding='SAME', name='deconv2')
        de_relu3 = tf.nn.relu(deconv3, 'de_relu3')

        print(latent_dim)
        print("Final deconv shape: {}".format(de_relu3.shape))
        
        fin_output = tf.reshape(de_relu3, [-1, latent_dim, num_generated_features])
        print("Generator final shape: {}".format(fin_output.shape))

        # print(output_2d.shape)
    #     output_3d = tf.reshape(output_2d, [-1, 20, num_generated_features])
    # #     print(output_3d.shape)
    # print('-----------------------------------------------------------------------------------------------------------------------')
    #return output_3d
    return fin_output

def discriminator(x, hidden_units_d, seq_length, batch_size, latent_dim,
                  reuse=False, cond_dim=0, c=None, batch_mean=False, parameters=None):
    with tf.variable_scope("discriminator") as scope:
        if reuse:
            scope.reuse_variables()
        if parameters is None:
            W_out_D = tf.get_variable(name='W_out_D', shape=[hidden_units_d, 1],
                    initializer=tf.truncated_normal_initializer())
            b_out_D = tf.get_variable(name='b_out_D', shape=1,
                    initializer=tf.truncated_normal_initializer())
        else:
            W_out_D = tf.get_variable(name='W_out_D', shape=[hidden_units_d, 1],
                                      initializer=tf.constant_initializer(
                                          value=parameters['discrimminator/W_out_D:0']
                                      ))
            b_out_D = tf.get_variable(name='b_out_D', shape=1,
                                      initializer=tf.constant_initializer(
                                          value=parameters['discrimminator/b_out_D:0']
                                      ))
       # W_final_D = tf.get_variable(name='W_final_D', shape=[hidden_units_d, 1],
       #         initializer=tf.truncated_normal_initializer())
       # b_final_D = tf.get_variable(name='b_final_D', shape=1,
       #         initializer=tf.truncated_normal_initializer())

        if cond_dim > 0:
            assert not c is None
            repeated_encoding = tf.stack([c]*seq_length, axis=1)
            inputs = tf.concat([x, repeated_encoding], axis=2)
        else:
            inputs = x
        # add the average of the inputs to the inputs (mode collapse?
        if batch_mean:
            mean_over_batch = tf.stack([tf.reduce_mean(x, axis=0)]*batch_size, axis=0)
            inputs = tf.concat([x, mean_over_batch], axis=2)

        ### First convolutional layer
        conv_1 = conv2d_layer(tf.reshape(inputs, [-1, latent_dim, 75, 1]), [5, 5, 1, 32], [32], 1, [1, 2, 3, 1],
                              [1, 1, 1, 1], [1, 2, 3, 1], 'SAME')
        print("Discrimminator Conv1_output: {}".format(conv_1.shape))

        ### Second convolutional layer
        conv_2 = conv2d_layer(conv_1, [4, 4, 32, 64], [64], 2, [1, 3, 3, 1], [1, 1, 1, 1], [1, 3, 3, 1], 'SAME')
        print("Discrimminator Conv2_output: {}".format(conv_2.shape))

        ### Third convolutional layer
        conv_3 = conv2d_layer(conv_2, [2, 2, 64, 64], [64], 3, [1, 3, 3, 1], [1, 1, 1, 1], [1, 3, 3, 1], 'SAME')
        print("Discrimminator Conv3_output: {}".format(conv_3.shape))

        cell = tf.contrib.rnn.LSTMCell(num_units=hidden_units_d, 
                state_is_tuple=True,
                reuse=reuse)
        # output_prob = 0.9
        # state_prob = 0.9
        #dropout_cell = DropoutWrapper(cell, output_keep_prob=output_prob, state_keep_prob=state_prob)
        rnn_outputs, rnn_states = tf.nn.dynamic_rnn(
            cell=cell,
            dtype=tf.float32,
            inputs=tf.reshape(conv_3, [-1, 1, 3]))
#        logit_final = tf.matmul(rnn_outputs[:, -1], W_final_D) + b_final_D
        logits = tf.einsum('ijk,km', rnn_outputs, W_out_D) + b_out_D
#        rnn_outputs_flat = tf.reshape(rnn_outputs, [-1, hidden_units_d])
#        logits = tf.matmul(rnn_outputs_flat, W_out_D) + b_out_D
        output = tf.nn.sigmoid(logits)
    #return output, logits, logit_final
    return output, logits

# --- to do with saving/loading --- #

def dump_parameters(identifier, sess):
    """
    Save model parmaters to a numpy file
    """
    dump_path = './experiments/parameters/' + identifier + '.npy'
    model_parameters = dict()
    for v in tf.trainable_variables():
        model_parameters[v.name] = sess.run(v)
    np.save(dump_path, model_parameters)
    print('Recorded', len(model_parameters), 'parameters to', dump_path)
    return True

def load_parameters(identifier):
    """
    Load parameters from a numpy file
    """
    load_path = './experiments/parameters/' + identifier + '.npy'
    model_parameters = np.load(load_path).item()
    return model_parameters

# --- to do with trained models --- #
def generate_continous_sequence(settings, epoch, num_samples, Z_samples, G_net, Z, latent_dim, sess=None):
    inputs = Z_samples
    if type(settings) == str:
        settings_dict = json.load(open('./experiments/settings/' + settings + '.txt', 'r'))
    #parameters = load_parameters(settings['identifier'] + '_' + str(epoch))
    #Z = tf.placeholder(tf.float32, [1, settings['seq_length']-3, settings['num_generated_features']])
    #G_net = generator(Z, settings['hidden_units_g'], settings['seq_length']-3, 1,
    #                    settings['num_generated_features'], reuse=False, parameters=parameters,
    #                    cond_dim=settings['cond_dim'])
    output_sequence = np.zeros(Z_samples.shape)#(num_samples, settings['num_generated_features']))
    #output_sequence[:settings['seq_length']-latent_dim, :] = Z_samples
    #length = Z_samples.shape[1]
    #predicted_vals = np.zeros((num_samples))

    if sess is None:
        sess = tf.Session()
        sess.run(tf.global_variables_initializer())
    data = Z_samples
    #while length<num_samples:
    result = sess.run(G_net, feed_dict={Z: data})
    print(result.shape)
    #    output_sequence[length:length+3, :] = result.reshape(-1, settings['num_generated_features'])
    #    predicted_vals[length:length+3] = np.ones((3))
    #    data[:, :-6, :] = data[:, 3:-3, :]
    #    data[:, -3:, :] = result
    #    length += 3
    #print(output_sequence.shape)
    #return output_sequence
    return result
#
# def sample_trained_model(settings, epoch, num_samples, data, Z_samples=None, C_samples=None):
#     """
#     Return num_samples samples from a trained model described by settings dict
#     """
#     # if settings is a string, assume it's an identifier and load
#     if type(settings) == str:
#         settings = json.load(open('./experiments/settings/' + settings + '.txt', 'r'))
#     print('Sampling', num_samples, 'samples from', settings['identifier'], 'at epoch', epoch)
#     # get the parameters, get other variables
#     parameters = load_parameters(settings['identifier'] + '_' + str(epoch))
#     # create placeholder, Z samples
#     Z = tf.placeholder(tf.float32, [num_samples, settings['seq_length']-3, settings['num_generated_features']])
#     CG = tf.placeholder(tf.float32, [num_samples, settings['cond_dim']])
#     if Z_samples is None:
#         Z_samples = sample_Z(num_samples, settings['seq_length'], settings['num_generated_features'], data,
#                                 settings['use_time'], use_noisy_time=False)
#     else:
#         assert Z_samples.shape[0] == num_samples
#     # create the generator (GAN or CGAN)
#     if C_samples is None:
#         # normal GAN
#         G_samples = generator(Z, settings['hidden_units_g'], settings['seq_length']-3,
#                               num_samples, settings['num_generated_features'],
#                               reuse=False, parameters=parameters, cond_dim=settings['cond_dim'])
#     else:
#         assert C_samples.shape[0] == num_samples
#         # CGAN
#         G_samples = generator(Z, settings['hidden_units_g'], settings['seq_length'],
#                               num_samples, settings['num_generated_features'],
#                               reuse=False, parameters=parameters, cond_dim=settings['cond_dim'], c=CG)
#     # sample from it
#     with tf.Session() as sess:
#         sess.run(tf.global_variables_initializer())
#         if C_samples is None:
#             real_samples = sess.run(G_samples, feed_dict={Z: Z_samples})
#         else:
#             real_samples = sess.run(G_samples, feed_dict={Z: Z_samples, CG: C_samples})
#     tf.reset_default_graph()
#     # sample from it
#     #sample_shape = list(Z_samples.shape)
#     #sample_shape[1] = 2
#     #real_samples = np.zeros(tuple(sample_shape))
#     #with tf.Session() as sess:
#     #    for i in range(0, num_samples, 28):
#     #        inputs = np.zeros((28, Z_samples.shape[1], Z_samples.shape[2]))
#     #        inputs[:min(28, num_samples-i)] = Z_samples[i:i+28]
#     #        sess.run(tf.global_variables_initializer())
#     #        if C_samples is None:
#     #            output = sess.run(G_samples, feed_dict={Z: inputs})
#     #        else:
#     #            output = sess.run(G_samples, feed_dict={Z: Z_samples, CG: C_samples})
#     #        print(i, num_samples)
#     #        real_samples[i:min(i+28, num_samples)] = output[:min(28, num_samples-i)]
#     #tf.reset_default_graph()
#     return real_samples

# --- to do with inversion --- #

# def invert(settings, epoch, samples, g_tolerance=None, e_tolerance=0.1,
#         n_iter=None, max_iter=10000, heuristic_sigma=None, C_samples=None):
#     """
#     Return the latent space points corresponding to a set of a samples
#     ( from gradient descent )
#     """
#     # cast samples to float32
#     samples = np.float32(samples[:, :, :])
#     # get the model
#     if type(settings) == str:
#         settings = json.load(open('./experiments/settings/' + settings + '.txt', 'r'))
#     num_samples = samples.shape[0]
#     print('Inverting', num_samples, 'samples using model', settings['identifier'], 'at epoch', epoch,)
#     if not g_tolerance is None:
#         print('until gradient norm is below', g_tolerance)
#     else:
#         print('until error is below', e_tolerance)
#     # get parameters
#     parameters = load_parameters(settings['identifier'] + '_' + str(epoch))
#     # assertions
#     assert samples.shape[2] == settings['num_generated_features']
#     # create VARIABLE Z
#     Z = tf.get_variable(name='Z', shape=[num_samples, settings['seq_length']],
#                         initializer=tf.random_normal_initializer())
#     if C_samples is None:
#         # create outputs
#         G_samples = generator(Z, settings['hidden_units_g'], settings['seq_length'],
#                               num_samples, settings['num_generated_features'],
#                               reuse=False, parameters=parameters)
#         fd = None
#     else:
#         CG = tf.placeholder(tf.float32, [num_samples, settings['cond_dim']])
#         assert C_samples.shape[0] == samples.shape[0]
#         # CGAN
#         G_samples = generator(Z, settings['hidden_units_g'], settings['seq_length'],
#                               num_samples, settings['num_generated_features'],
#                               reuse=False, parameters=parameters, cond_dim=settings['cond_dim'], c=CG)
#         fd = {CG: C_samples}
#
#     # define loss
#     if heuristic_sigma is None:
#         heuristic_sigma = mmd.median_pairwise_distance(samples)     # this is noisy
#         print('heuristic_sigma:', heuristic_sigma)
#     Kxx, Kxy, Kyy, wts = mmd._mix_rbf_kernel(G_samples, samples, sigmas=tf.constant(value=heuristic_sigma, shape=(1, 1)))
#     similarity_per_sample = tf.diag_part(Kxy)
#     reconstruction_error_per_sample = 1 - similarity_per_sample
#     #reconstruction_error_per_sample = tf.reduce_sum((tf.nn.l2_normalize(G_samples, dim=1) - tf.nn.l2_normalize(samples, dim=1))**2, axis=[1,2])
#     similarity = tf.reduce_mean(similarity_per_sample)
#     reconstruction_error = 1 - similarity
#     # updater
# #    solver = tf.train.AdamOptimizer().minimize(reconstruction_error_per_sample, var_list=[Z])
#     #solver = tf.train.RMSPropOptimizer(learning_rate=500).minimize(reconstruction_error, var_list=[Z])
#     solver = tf.train.RMSPropOptimizer(learning_rate=0.1).minimize(reconstruction_error_per_sample, var_list=[Z])
#     #solver = tf.train.MomentumOptimizer(learning_rate=0.1, momentum=0.9).minimize(reconstruction_error_per_sample, var_list=[Z])
#
#     grad_Z = tf.gradients(reconstruction_error_per_sample, Z)[0]
#     grad_per_Z = tf.norm(grad_Z, axis=(1, 2))
#     grad_norm = tf.reduce_mean(grad_per_Z)
#     #solver = tf.train.GradientDescentOptimizer(learning_rate=0.1).minimize(reconstruction_error, var_list=[Z])
#     print('Finding latent state corresponding to samples...')
#     with tf.Session() as sess:
#         sess.run(tf.global_variables_initializer())
#         error = sess.run(reconstruction_error, feed_dict=fd)
#         g_n = sess.run(grad_norm, feed_dict=fd)
#         print(g_n)
#         i = 0
#         if not n_iter is None:
#             while i < n_iter:
#                 _ = sess.run(solver, feed_dict=fd)
#                 error = sess.run(reconstruction_error, feed_dict=fd)
#                 i += 1
#         else:
#             if not g_tolerance is None:
#                 while g_n > g_tolerance:
#                     _ = sess.run(solver, feed_dict=fd)
#                     error, g_n = sess.run([reconstruction_error, grad_norm], feed_dict=fd)
#                     i += 1
#                     print(error, g_n)
#                     if i > max_iter:
#                         break
#             else:
#                 while np.abs(error) > e_tolerance:
#                     _ = sess.run(solver, feed_dict=fd)
#                     error = sess.run(reconstruction_error, feed_dict=fd)
#                     i += 1
#                     print(error)
#                     if i > max_iter:
#                         break
#         Zs = sess.run(Z, feed_dict=fd)
#         error_per_sample = sess.run(reconstruction_error_per_sample, feed_dict=fd)
#         print('Z found in', i, 'iterations with final reconstruction error of', error)
#     tf.reset_default_graph()
#     return Zs, error_per_sample, heuristic_sigma