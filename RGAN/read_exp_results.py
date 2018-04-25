import os
import numpy as np

d_time_list = []
g_time_list = []
home_dir = 'experiments/data'

d_file_substr = 'D_train_time_'
g_file_substr = 'G_train_time_'

files_list = os.listdir(home_dir)
total_time = []
rows = None
value_printed = False
total_time = 0
for file_name in files_list:
    if d_file_substr in file_name:
        temp_array = np.load(os.path.join(home_dir, file_name))
        if not value_printed:
            print(temp_array.shape[0])
            value_printed=True
            rows = temp_array.shape[0]
        name, ext = os.path.splitext(file_name)
        idx = name.replace(d_file_substr, '')
        d_time_list.append((int(idx), np.mean(temp_array, axis=0), np.mean(np.sum(temp_array, axis=1))))
        total_time += d_time_list[-1][2]
    elif g_file_substr in file_name:
        temp_array = np.load(os.path.join(home_dir, file_name))
        if not value_printed:
            print(temp_array.shape[0])
            value_printed=True
            rows = temp_array.shape[0]
        name, ext = os.path.splitext(file_name)
        idx = name.replace(g_file_substr, '')
        g_time_list.append((int(idx), np.mean(temp_array, axis=0), np.mean(np.sum(temp_array, axis=1))))
        total_time += g_time_list[-1][2]
d_time_list.sort()
g_time_list.sort()

print('---------------------------------------------------------------------------------------------------')
print('Time periods for discrimminator:')
print(d_time_list)
print('---------------------------------------------------------------------------------------------------')
print('Time periods for generator:')
print(g_time_list)
print('---------------------------------------------------------------------------------------------------')
print('Total time that should be taken:')
print(rows * total_time)
print('---------------------------------------------------------------------------------------------------')
