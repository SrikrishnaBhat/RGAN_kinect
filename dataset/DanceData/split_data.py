import os
import pandas as pd
import numpy as np


home_dir = 'parsed'
result_dir = '../../RGAN_forecasting/data'

if not os.path.exists(result_dir):
    os.makedirs(result_dir)

file_list = os.listdir(home_dir)
ROWS = 80 #Number of rows or timesteps
STRIDE = 3
COLUMNS = 75

def get_len_from_dir(file_list):
    global home_dir
    n_samples = 0
    for file_name in file_list:
        rows = pd.read_csv(os.path.join(home_dir, file_name)).values.shape[0]
        n_samples += (rows - ROWS)/STRIDE
    return n_samples

def centre_points(arr):
    shape = arr.shape
    for i in range(shape[0]):
        X_orig = np.array([500 - arr[i, 0], 600 - arr[i, 1], 300 - arr[i, 2]])
        for j in range(0, shape[1], 3):
            arr[i, j:j+3] = arr[i, j:j+3] + X_orig
    return arr

n_samples = get_len_from_dir(file_list)

SPLIT_RATIO = np.array([0.6, 0.2, 0.2])
split_length = (n_samples * SPLIT_RATIO).astype('int64')

data_dict = {
    'train': np.zeros((split_length[0], ROWS, COLUMNS)),
    'test': np.zeros((split_length[1], ROWS, COLUMNS)),
    'vali': np.zeros((split_length[2], ROWS, COLUMNS))
}

indexing = np.zeros(3).astype('int64')

column_list = []

## Create the column names ##
for i in range(25):
    for j in range(3):
        column_list.append('j' + str(i) + 'x' + str(j))

for file_name in file_list:
    print(file_name)
    input_df = pd.read_csv(os.path.join(home_dir, file_name))
    input_array = input_df.values
    array_shape = input_array.shape
    inter_array = np.zeros((int((array_shape[0] - ROWS)/STRIDE), ROWS, COLUMNS))
    ## Get as many rows as ROWS value
    for i in range(0, input_array.shape[0]-ROWS, STRIDE):
        start = i
        temp_array = np.zeros((ROWS, input_array.shape[1]))
        temp_array[:ROWS, :] = input_array[start:start+ROWS, :]
        inter_array[start:start + ROWS, :, :] = centre_points(temp_array)
    np.random.shuffle(inter_array)
    proportions = (inter_array.shape[0] * SPLIT_RATIO).astype('int64')
    data_dict['train'][indexing[0]:indexing[0] + proportions[0], :, :] = inter_array[:proportions[0], :, :]
    data_dict['test'][indexing[1]:indexing[1] + proportions[1], :, :] = inter_array[proportions[0]:sum(proportions[:2]), :, :]
    data_dict['vali'][indexing[2]:indexing[2] + proportions[2], :, :] = inter_array[sum(proportions[:2]): sum(proportions), :, :]
    indexing += proportions

np.save(os.path.join(result_dir, 'dance_data.npy'), data_dict)
