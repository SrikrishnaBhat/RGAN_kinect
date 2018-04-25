import numpy as np
import pandas as pd

input_file = '../../RGAN_forecasting/experiments/data/dance_data_norm.data.npy'
min_file = '../../RGAN_forecasting/experiments/data/cristobal_dance_min.npy'
max_file = '../../RGAN_forecasting/experiments/data/cristobal_dance_max.npy'

## de min-max normalize input function
def de_normalize(input):
    max_list = np.load(max_file)
    min_list = np.load(min_file)
    for i in range(len(max_list)):
        input[:, i] = (input[:, i] + 1)/2
        input[:, i] = (input[:, i] * (max_list[i] - min_list[i])) + min_list[i]
    return input

output_file = 'dance_gen/merged_data.csv'
input_array = np.load(input_file).item()['train']
input_dims = input_array.shape
print(input_dims)

print(input_dims)

shrink_size = 200

input_seq = np.zeros((shrink_size * input_dims[1], input_dims[2]))
for i in range(shrink_size):
    print(i)
    input_seq[i*input_dims[1]: (i+1)*input_dims[1], :] = de_normalize(input_array[i, :, :])
print(input_seq.shape)

output_df = pd.DataFrame(input_seq)
output_df.to_csv(output_file, index=False)
