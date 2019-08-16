import pandas as pd
import numpy as np
from celery import Task, shared_task
from django.db import transaction

from datasets.models import Dataset, Signal, Sample, Tag, SignalChunkFile, Analysis
from datasets.constants import process_status, signal_types

import logging
logger = logging.getLogger(__name__)

class DatasetTask(Task):

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        dataset = Dataset.objects.get(id=args[1])
        dataset.status = process_status.ERROR
        dataset.save()

class AnalysisTask(Task):

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        analysis = Analysis.objects.get(id=args[0])
        analysis.status = process_status.ERROR
        analysis.save()

def save_to_sample_table(series, signal):
    samples = [
        Sample(
            timestamp=index,
            value=value,
            signal=signal
        )
        for index, value
        in series.items()
    ]
    Sample.objects.bulk_create(samples)

def save_to_tag_table(series, signal):
    tags = [
        Tag(
            timestamp=index,
            value=value,
            signal=signal
        )
        for index, value
        in series.items()
    ]
    Tag.objects.bulk_create(tags)

def save_to_signal_file(series, signal):
    CHUNK_LENGTH = 3600
    lower_bound = series.index.min()
    lower_bound = lower_bound - pd.Timedelta(
        microseconds=lower_bound.microsecond
    )
    upper_bound = lower_bound + pd.Timedelta(seconds=CHUNK_LENGTH)

    while lower_bound < series.index.max():
        chunk = series[(series.index >= lower_bound) & (series.index < upper_bound)]
        if not chunk.empty:
            signal_file = SignalChunkFile(
                signal=signal,
                first_timestamp=chunk.index.min(),
                last_timestamp=chunk.index.max(),
                user_id=signal.user_id,
            )
            signal_file.save_to_disk(chunk)
            signal_file.save()

        lower_bound = upper_bound
        upper_bound = lower_bound + pd.Timedelta(seconds=CHUNK_LENGTH)

def save_parsed_signals(dataset, signals):
    signal_ids = []

    for signal_name, data in signals.items():
        signal_type = data.get('type', signal_types.OTHER)
        series = data['series']

        y_min = None
        y_max = None
        if np.issubdtype(series.dtype, np.number):
            y_min = series.min()
            y_max = series.max()

        signal = Signal(
            name=signal_name,
            dataset=dataset,
            type=signal_type,
            raw_file_id=data.get('raw_file_id'),
            frequency=data.get('frequency'),
            unit=data.get('unit'),
            first_timestamp=series.first_valid_index(),
            last_timestamp=series.last_valid_index(),
            y_min=y_min,
            y_max=y_max,
            user_id=dataset.user_id,
        )
        signal.save()
        signal_ids.append(signal.id)

        if signal_type in [signal_types.NN_INTERVAL, signal_types.RR_INTERVAL]:
            save_to_sample_table(series, signal)
        elif signal_type is signal_types.TAGS:
            save_to_tag_table(series, signal)
        else:
            save_to_signal_file(series, signal)

    return signal_ids


@shared_task(base=DatasetTask)
def parse_raw_files(file_ids, dataset_id):
    dataset = Dataset.objects.get(id=dataset_id)
    dataset.status = process_status.PROCESSING
    dataset.save()
    result = dataset.source.parse(file_ids)

    for value in result.values():
        value['series'].dropna(inplace=True)

    with transaction.atomic():
        signal_ids = save_parsed_signals(dataset, result)
        dataset.status = process_status.PROCESSED
        dataset.save()

    return signal_ids

@shared_task(base=AnalysisTask)
def start_analysis(analysis_id):
    analysis = Analysis.objects.get(id=analysis_id)
    analysis.status = process_status.PROCESSING
    analysis.save()

    analysis.result = analysis.compute()
    analysis.status = process_status.PROCESSED
    analysis.save()

    return analysis_id
