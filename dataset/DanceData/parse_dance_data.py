import os
import pandas as pd
import numpy as np

# Joint positions in the original data
CENTRE = [0, 1, 2, 3, 20]
LEFT = [4, 5, 6, 7, 12, 13, 14, 15, 21, 22]
RIGHT = [8, 9, 10,11, 16, 17, 18, 19, 23, 24]

### Functions to segregate out each part
def centre(input_array):
    output_array = np.zeros((1, 15))
    i=0
    for index in CENTRE:
        output_array[:, i*3: i*3 + 3] = input_array[index, 3:]
        i+=1
    return output_array

def left_part(input_array):
    output_array = np.zeros((1, 30))
    i=0
    for index in LEFT:
        output_array[:, i*3: i*3 + 3] = input_array[index, 3:]
        i+=1
    return output_array

def right_part(input_array):
    output_array = np.zeros((1, 30))
    i=0
    for index in RIGHT:
        output_array[:, i*3: i*3 + 3] = input_array[index, 3:]
        i+=1
    return output_array

def parse_dance_data(input_df):
    input_arr = input_df.values
    dims = input_arr.shape
    final_array = np.zeros((dims[0]/25, 75))
    for i in range(0, dims[0], 25):
        temp_arr = input_arr[i:i+25, :]
        final_array[i/25, :15] = centre(temp_arr)
        final_array[i/25, 15:45] = left_part(temp_arr)
        final_array[i/25, 45:75] = right_part(temp_arr)
    return final_array

home_dir = 'Double Agent'
result_dir = 'parsed'
file_list = os.listdir(home_dir)

### Create result directory if it doesn't exist
if not os.path.exists(result_dir):
    os.makedirs(result_dir)

for file_name in file_list:
    print(file_name)
    dance_df = pd.read_csv(os.path.join(home_dir, file_name))
    parsed_df = pd.DataFrame(parse_dance_data(dance_df))
    parsed_df.to_csv(os.path.join(result_dir, file_name.split('.')[0] + '_parsed.csv'), index=None)
