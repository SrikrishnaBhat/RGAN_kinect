import pandas as pd
import numpy as np

columns = []
for i in range(25):
    for j in range(3):
        columns.append('j{}x{}'.format(i, j))

input_file = 'merged_synthetic_data.csv'
input_df = pd.read_csv(input_file)
output_df = input_df.loc[:, columns]
output_df.to_csv('merged_dance_synthetic.csv', index=None)
