import pandas as pd
import numpy as np
import os

home_dir = 'experiments/data/kinect_sequence'

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

synth_df = pd.DataFrame(final_array, columns = column_list)
identity_array = np.ones((synth_df.values.shape[0], 25))
final_df = synth_df.join(pd.DataFrame(identity_array, columns=new_columns))
final_df = final_df[final_columns]
final_df.to_csv('parsed_synthetic_merged_data.csv', index=None)
