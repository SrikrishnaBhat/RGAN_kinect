import numpy as np

input_file = 'dance_data.npy'
output_file = '../../RGAN/experiments/data/dance_data_norm.data.npy'
identifier = 'cristobal_dance'

def min_max_normalize(identifier, samples):
    max_list = []
    min_list = []
    shape = samples['train'].shape
    train = samples['train']
    test = samples['test']
    vali = samples['vali']
    for i in range(shape[-1]):
        max_list.append(max([train[:, :, i].max(), test[:, :, i].max(), vali[:, :, i].max()]))
        min_list.append(min([train[:, :, i].min(), test[:, :, i].min(), vali[:, :, i].min()]))
        if max_list[i] != min_list[i]:
            train[:, :, i] = (train[:, :, i] - min_list[i])/(max_list[i]-min_list[i])
            test[:, :, i] = (test[:, :, i] - min_list[i])/(max_list[i]-min_list[i])
            vali[:, :, i] = (vali[:, :, i] - min_list[i])/(max_list[i]-min_list[i])
        else:
            train[:, :, i] = np.ones(train[:, :, i].shape)
            test[:, :, i] = np.ones(test[:, :, i].shape)
            vali[:, :, i] = np.ones(vali[:, :, i].shape)
        train[:, :, i] = train[:, :, i] * 2 - 1
        test[:, :, i] = test[:, :, i] * 2 - 1
        vali[:, :, i] = vali[:, :, i] * 2 - 1
    np.save('../../RGAN/experiments/data/{}_max.npy'.format(identifier), max_list)
    np.save('../../RGAN/experiments/data/{}_min.npy'.format(identifier), min_list)
    samples['train'] = train
    samples['test'] = test
    samples['vali'] = vali
    return samples

samples = min_max_normalize(identifier, np.load(input_file).tolist())
np.save(output_file, samples)
