import numpy as np

input_file = '../../RGAN_forecasting/data/dance_data.npy'
output_file = '../../RGAN_forecasting/experiments/data/dance_data_norm.data.npy'
identifier = 'cristobal_dance'

def min_max_normalize(identifier, samples):
    max_list = []
    min_list = []
    train, test, vali = samples['train'], samples['test'], samples['vali']
    shape = train.shape
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
         test[:, :, i] = vali[:, :, i] * 2 - 1
         vali[:, :, i] = vali[:, :, i] * 2 - 1
    np.save('../../RGAN_forecasting/experiments/data/{}_max.npy'.format(identifier), max_list)
    np.save('../../RGAN_forecasting/experiments/data/{}_min.npy'.format(identifier), min_list)
    return {'train': train, 'vali': vali, 'test': test}

samples = min_max_normalize(identifier, np.load(input_file).tolist())
np.save(output_file, samples)
