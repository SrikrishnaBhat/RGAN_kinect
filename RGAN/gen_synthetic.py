import numpy as np
import tensorflow as tf
import data_utils
import pandas as pd
import os

identifier = 'cristobal_dance'
epoch = 94
num_samples = 200

## Generate the synthetic data ##
data_utils.generate_synthetic(identifier, epoch, num_samples)

X_orig = np.array([500, 600, 300])

def de_centre_points(arr):
    shape = arr.shape
    for i in range(shape[0]):
        for j in range(0, shape[1], 3):
            arr[i, j:j+3] = arr[i, j:j+3] + X_orig
    return arr

## Merged the generated data ##
home_dir = 'experiments/data/kinect_sequence'
result_dir = 'experiments/data'
result_file = 'merged_synthetic_data.csv'

def centre_points(arr):
    shape = arr.shape
    for i in range(shape[0]):
        for j in range(0, shape[1], 3):
            arr[i, j:j+3] = arr[i, j:j+3] - X_orig
    return arr

input_list = os.listdir(home_dir)
print(input_list)

final_array = None
column_list = None

for file_name in input_list:
    input_df = pd.read_csv(os.path.join(home_dir, file_name))
    if column_list is None:
        column_list = input_df.columns.values
    if final_array is None:
        final_array = input_df.values
    else:
        print(file_name)
        final_array = np.append(final_array, input_df.values, axis=0)

joint_coords = 25
dims = 3

final_columns = []
new_columns = []

for i in range(joint_coords):
    for j in range(dims):
        col_name = 'j' + str(i) + 'x' + str(j)
        final_columns.append(col_name)
    final_columns.append('i' + str(i))
    new_columns.append('i' + str(i))

final_array = de_centre_points(final_array)

synth_df = pd.DataFrame(final_array, columns = column_list)
synth_df.to_csv(os.path.join(result_dir, 'merged_dance_synthetics_{}.csv'.format(epoch)), index=None)
identity_array = np.ones((synth_df.values.shape[0], 25))
final_df = synth_df.join(pd.DataFrame(identity_array, columns=new_columns))
final_df = final_df[final_columns]
final_df.to_csv(os.path.join(result_dir, result_file), index=None)
