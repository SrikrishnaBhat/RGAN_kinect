import numpy as np

input_file = 'dance_data.npy'
output_file = 'dance_data_norm.npy'
identifier = 'cristobal_dance'

def min_max_normalize(identifier, samples):
    max_list = []
    min_list = []
    shape = samples.shape
    for i in range(shape[-1]):
         max_list.append(samples[:, :, i].max())
         min_list.append(samples[:, :, i].min())
         if max_list[i] != min_list[i]:
            samples[:, :, i] = (samples[:, :, i] - min_list[i])/(max_list[i]-min_list[i])
         else:
            samples[:, :, i] = np.ones(samples[:, :, i].shape)
         samples[:, :, i] = samples[:, :, i] * 2 - 1
    np.save('../../RGAN/experiments/data/{}_max.npy'.format(identifier), max_list)
    np.save('../../RGAN/experiments/data/{}_min.npy'.format(identifier), min_list)
    return samples

samples = min_max_normalize(identifier, np.load(input_file))
np.save(output_file, samples)
