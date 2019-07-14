import os
import operator
import pandas as pd
import numpy as np
from datetime import datetime

def raw_file_path(instance, filename):
    path = "users/{username}/{dataset}/{filename}.{ext}".format(
        username=instance.user.username,
        dataset=instance.dataset_id,
        filename=instance.id,
        ext=filename.rpartition(".")[2]
    )
    return path

def signal_file_path(instance, filename):
    path = "users/{username}/{dataset}/{signal}/{filename}.{ext}".format(
        username=instance.user.username,
        dataset=instance.signal.dataset_id,
        signal=instance.signal_id,
        filename=instance.id,
        ext="csv"
    )
    return path

def search_dict(dict, search_for):
    for (key, value) in dict.items():
        if value == search_for:
            return key
    return None

def is_non_zero_file(path):
    return os.path.isfile(path) and os.path.getsize(path) > 0

def create_series(name, data, start_time, freq, dtype=None):
    if not dtype and hasattr(data, 'dtype'):
        dtype = data.dtype

    index = pd.date_range(
        start=pd.to_datetime(start_time, unit='s'),
        periods=len(data),
        freq='{}N'.format(int(1e9 / freq))
    )

    return pd.Series(
        name=name,
        data=data,
        index=index,
        dtype=dtype
    )

def create_df(signal_names, signals, sample_freqs, start_timestamps):
    base_freq_key = max(sample_freqs.items(), key=operator.itemgetter(1))[0]
    max_freq = sample_freqs[base_freq_key]
    min_start_timestamp = start_timestamps[base_freq_key]
    data_frame = pd.DataFrame(index=pd.date_range(start=pd.to_datetime(min_start_timestamp, unit='s'),
                                                  periods=len(signals[base_freq_key]),
                                                  freq='{}N'.format(int(1e9 / max_freq))))
    for signal in signal_names:
        date_index = pd.date_range(start=pd.to_datetime(start_timestamps[signal], unit='s'),
                                   periods=len(signals[signal]),
                                   freq='{}N'.format(int(1e9 / sample_freqs[signal])))
        signal_data_frame = pd.DataFrame(data=signals[signal],
                                         index=date_index,
                                         columns=[signal])
        data_frame = data_frame.join(signal_data_frame, how='outer', sort=True)
    return data_frame
