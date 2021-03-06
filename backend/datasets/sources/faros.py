import re
import pandas as pd
import numpy as np
import pyedflib
from datetime import datetime

from datasets.constants import signal_types
from datasets.utils import create_series
from datasets.sources.source_base import SourceBase

class FarosSource(SourceBase):

    META = {
        'ECG': {
            'type': signal_types.ECG
        },
        'HRV': {
            'type': signal_types.RR_INTERVAL,
            'unit': 'Milliseconds'
        },
    }

    @classmethod
    def name(cls):
        return "Faros"

    @classmethod
    def fileOptions(cls):
        return [
            {
                'label': 'EDF File',
                'pattern': '[\d-]{8}\.EDF',
                'required': True,
                'multiple': False,
                'timestamp': False
            }
        ]

    def parse(self):
        dtypes = {
            'ECG': np.int16,
            'HRV': np.int16, # allows for NaN values
            'Accelerometer_X': np.int16,
            'Accelerometer_Y': np.int16,
            'Accelerometer_Z': np.int16,
        }
        raw_file = self.raw_files[0]

        with pyedflib.EdfReader(raw_file.path.path) as f:
            signal_labels = f.getSignalLabels()
            sample_freqs = f.getSampleFrequencies()
            start_ts = (f.getStartdatetime() - datetime.fromtimestamp(0)).total_seconds()

            data = dict.fromkeys(dtypes)
            for index, label in enumerate(signal_labels):
                if label =='Accelerometer_X':
                    freq_acc = sample_freqs[index]
                if label in dtypes.keys():
                    data[label] = create_series(
                        name=label,
                        data=f.readSignal(index),
                        start_time=start_ts,
                        freq=sample_freqs[index],
                        dtype=dtypes[label]
                    )

        data['Accelerometer_MAG'] = create_series(
            name='Accelerometer_MAG',
            data=np.linalg.norm([data['Accelerometer_X'], data['Accelerometer_Y'], data['Accelerometer_Z']], axis=0),
            start_time=start_ts,
            freq=freq_acc
        )

        data['HRV'] = data['HRV'].replace(0, np.nan).dropna()

        for label in data.keys():
            data[label] = data[label].tz_localize('UTC', copy=False)

        result = {
            signal: {
                'raw_file_id': raw_file.id,
                'series': data[signal]
            }
            for signal
            in data.keys()
        }

        for name, meta in self.META.items():
            result[name] = {
                **result[name],
                **meta
            }

        return result
