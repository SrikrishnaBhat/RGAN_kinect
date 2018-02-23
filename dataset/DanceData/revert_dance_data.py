import os
import pandas as pd
import numpy as np

# Joint positions in the original data

joint_pos = [('SPINE_BASE', 0), ('SPINE_MID', 1), ('NECK', 2), ('HEAD', 3), ('LEFT_SHOULDER', 5), ('LEFT_ELBOW', 6), ('LEFT_WRIST', 7), 
               ('LEFT_HAND', 8), ('RIGHT_SHOULDER', 15), ('RIGHT_ELBOW', 16), ('RIGHT_WRIST', 17), ('RIGHT_HAND', 18), ('LEFT_HIP', 9),
               ('LEFT_KNEE', 10), ('LEFT_ANKLE', 11), ('LEFT_FOOT', 12), ('RIGHT_HIP', 19), ('RIGHT_KNEE', 20), ('RIGHT_ANKLE', 21),
               ('RIGHT_FOOT', 22), ('SPINE_SHOULDER', 4), ('LEFT_HANDTIP', 13), ('LEFT_THUMB', 14), ('RIGHT_HANDTIP', 23), ('RIGHT_THUMB', 24)]

def revert_dance_data(input_df):
    input_arr = input_df.values
    dims = input_arr.shape
    time, index = 0, 0
    dancer = 1
    final_array = np.zeros((dims[0]*25, 6)).astype(object)
    for i in range(0, dims[0]):
        for (joint, pos) in joint_pos:
            x = input_arr[i, pos*3 + 0]
            y = input_arr[i, pos*3 + 1]
            z = input_arr[i, pos*3 + 2]
            temp_arr = [time, dancer, joint, x, y, z]
            final_array[index, :] = np.array(temp_arr)
            index += 1
        time += 1
    return final_array

home_dir = 'dance_gen'
result_dir = home_dir + '_reverted'
file_list = os.listdir(home_dir)

column_list = ['time', 'dancer', 'joint', 'x', 'y', 'z']

### Create result directory if it doesn't exist
if not os.path.exists(result_dir):
    os.makedirs(result_dir)

for file_name in file_list:
    print(file_name)
    dance_df = pd.read_csv(os.path.join(home_dir, file_name))
    parsed_df = pd.DataFrame(revert_dance_data(dance_df), columns=column_list)
    parsed_df.to_csv(os.path.join(result_dir, file_name.split('.')[0] + '_reverted.csv'), index=None)

