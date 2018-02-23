import os
import pandas
import numpy as np

home_dir = 'parsed'
result_dir = 'G_sequences'

if not os.path.exists(result_dir):
    os.makedirs(result_dir)

file_list = os.listdir(home_dir)
ROWS = 20 #Number of rows or timesteps

def centre_points(arr):
    shape = arr.shape
    for i in range(shape[0]):
        for j in range(0, shape[1], 3):
            arr[i, j:j+3] = arr[i, j:j+3] - X_orig
    return arr

X_orig = np.array([500, 600, 300])

indexing = 0

column_list = []

## Create the column names ##
for i in range(25):
    for j in range(3):
        column_list.append('j' + str(i) + 'x' + str(j))

for file_name in file_list:
    print(file_name)
    input_df = pandas.read_csv(os.path.join(home_dir, file_name))
    input_array = input_df.values
    if indexing==0:
        X_orig = np.array([500 - input_array[0, 0], 600 - input_array[0, 1], 300 - input_array[0, 2]])
    ## Get as many rows as ROWS value
    for i in range(0, input_array.shape[0]):
        diff = min(ROWS, input_array.shape[0]-i)

        ## Pad zeroes to the array if number of rows is less than ROWS
        start = i
        temp_array = np.zeros((ROWS, input_array.shape[1]))
        temp_array[:diff, :] = input_array[start:start+diff, :]
        temp_array = centre_points(temp_array)
        output_df = pandas.DataFrame(temp_array, columns=column_list)
        name = file_name.split('.')[0] + str(i) + '.csv'
        output_df.to_csv(os.path.join(result_dir, name), index=None)
    indexing += 1
