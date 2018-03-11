import os
import pandas
import numpy as np

home_dir = 'parsed'
result_dir = 'G_sequences'

if not os.path.exists(result_dir):
    os.makedirs(result_dir)

file_list = os.listdir(home_dir)
ROWS = 60 #Number of rows or timesteps
STRIDE = 3

def centre_points(arr):
    shape = arr.shape
    for i in range(shape[0]):
        X_orig = np.array([500 - arr[i, 0], 600 - arr[i, 1], 300 - arr[i, 2]])
        for j in range(0, shape[1], 3):
            arr[i, j:j+3] = arr[i, j:j+3] + X_orig
    return arr

def get_num_rows(files_list):
	num_rows = 0
	for file_name in files_list:
		num_rows += pandas.read_csv(os.path.join(home_dir, file_name)).values.shape[0]
	return num_rows
indexing = 0

column_list = []

SPLIT_RATIO = np.array([0.6, 0.2, 0.2])
num_rows = get_num_rows(file_list)
PROPORTIONS = ((num_rows-ROWS)/STRIDE * SPLIT_RATIO).astype('int64')

print(PROPORTIONS)

dance_data = {
	'train': np.zeros((PROPORTIONS[0], ROWS, 75)),
	'test': np.zeros((PROPORTIONS[1], ROWS, 75)),
	'vali': np.zeros((PROPORTIONS[2], ROWS, 75))
}

## Create the column names ##
for i in range(25):
    for j in range(3):
        column_list.append('j' + str(i) + 'x' + str(j))

beg = np.array([0, 0, 0])
for file_name in file_list:
    print(file_name)
    input_df = pandas.read_csv(os.path.join(home_dir, file_name))
    input_array = input_df.values
    temp_array = np.zeros((int((input_array.shape[0]-ROWS)/STRIDE), ROWS, 75))
    for i in range(0, input_array.shape[0]-ROWS, STRIDE):
        start = i
        # temp_array = np.zeros((ROWS, input_array.shape[1]))
        end = min(ROWS, input_array.shape[0]-i)
        temp_array[indexing, start:end,:] = centre_points(input_array[start:end, :])
        # output_df = pandas.DataFrame(temp_array, columns=column_list)
        # name = file_name.split('.')[0] + str(i) + '.csv'
        # output_df.to_csv(os.path.join(result_dir, name), index=None)
    np.random.shuffle(temp_array)
    props = (SPLIT_RATIO * temp_array.shape[0]).astype('int64')
    partition = np.array([props[:1].sum(), props[:2].sum(), props[:3].sum()])
    print(props)
    print(partition)
    print(beg)
    dance_data['train'][beg[0]:beg[0]+props[0], :, :] = temp_array[:partition[0], :, :]
    dance_data['test'][beg[1]:beg[1]+props[1], :, :] = temp_array[partition[0]:partition[1], :, :]
    dance_data['vali'][beg[2]:beg[2]+props[2], :, :] = temp_array[partition[1]:partition[2], :, :]
    indexing += 1
    beg += props

np.save('dance_data.npy', dance_data)
