import numpy as np
import pandas as pd
import os

home_dir = 'G_sequences'
input_file_list = os.listdir(home_dir)
identifier = 'cristobal_dance'
out_file = 'dance_data.npy'

def min_max_normalize(identifier, samples):
    max_list = []
    min_list = []
    shape = samples.shape
    for i in range(shape[-1]):
         max_list.append(samples[:, :, i].max())
         min_list.append(samples[:, :, i].min())
         samples[:, :, i] = (samples[:, :, i] - min_list[i])/(max_list[i]-min_list[i])
         samples[:, :, i] = samples[:, :, i] * 2 - 1
    np.save('../../RGAN/experiments/data/{}_max.npy'.format(identifier), max_list)
    np.save('../../RGAN/experiments/data/{}_min.npy'.format(identifier), min_list)
    return samples

samples = np.ones([0, 20, 75])
for input_file in input_file_list:
    image_df = pd.read_csv(os.path.join(home_dir, input_file))
    image_values = image_df.values
    if image_values.shape[0]!=20:
        continue
    samples = np.append(samples, image_values.reshape(1, 20, -1), axis=0)

np.save(out_file, samples)
