import numpy as np
import pandas as pd

input_file = 'dance_data_shrinked.npy'
min_file = '../../RGAN/experiments/data/cristobal_dance_min.npy'
max_file = '../../RGAN/experiments/data/cristobal_dance_max.npy'

## de min-max normalize input function
def de_normalize(input):
    max_list = np.load(max_file)
    min_list = np.load(min_file)
    for i in range(len(max_list)):
        input[:, i] = (input[:, i] + 1)/2
        input[:, i] = (input[:, i] * (max_list[i] - min_list[i])) + min_list[i]
    return input

SEQ_LENGTH = 20

output_file = 'dance_gen/merged_data.csv'
input_array = np.load(input_file)
input_dims = input_array.shape
print(input_dims)

print(input_dims)

input_seq = np.zeros((input_dims[0] * input_dims[1], input_dims[2]))
for i in range(input_dims[0]/10):
    print(i)
    input_seq[i*SEQ_LENGTH: (i+1)*SEQ_LENGTH, :] = de_normalize(input_array[i, :, :])

output_df = pd.DataFrame(input_seq)
output_df.to_csv(output_file, index=False)