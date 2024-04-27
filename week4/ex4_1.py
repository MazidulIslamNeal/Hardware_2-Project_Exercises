import micropython
from filefifo import Filefifo

previous_slop_sign = 0

file_path = "capture01_250Hz.txt"

data = Filefifo(10, name=file_path)

peak_count = 0
slope = 0

interval_between_data_points = 4  # as 250 samples is in one second so there will be one sample in every 4 ms.
sample_count_between_2_seconds = 2000 / interval_between_data_points

current_time = 0

peaks = []

calculation_frame = []

calculation_frame_max = None
calculation_frame_min = None
frame_peaks = []

peak_store_count = 0

previous_peak_time = 0
for _ in range(25931):
    sample = data.get()

    calculation_frame.append((current_time, sample))

    if calculation_frame_max == None:
        calculation_frame_max = sample
    else:
        if calculation_frame_max < sample:
            calculation_frame_max = sample

    if calculation_frame_min == None:
        calculation_frame_min = sample
    else:
        if calculation_frame_min > sample:
            calculation_frame_min = sample

    previous_datapoint = None

    if len(calculation_frame) == sample_count_between_2_seconds:
        threshold = (calculation_frame_max + calculation_frame_min) / 2
        for frame_sample in calculation_frame:
            value = frame_sample[1]
            frame_time = frame_sample[0]
            if value > threshold:
                if previous_datapoint != None:
                    slope = (value - previous_datapoint)

                    if previous_slop_sign >= 0 and slope < 0:
                        if previous_peak_time == 0 or frame_time - previous_peak_time >= 250:
                            peak_count = peak_count + 1
                            frame_peaks.append((frame_time, value))
                            peaks.append((frame_time, value))
                            if previous_peak_time != 0:
                                bpm = int(60000 / ((frame_time - previous_peak_time)))
                                if (bpm > 30):
                                    print(bpm)

                            previous_peak_time = frame_time

                previous_datapoint = value
                previous_slop_sign = slope

        calculation_frame = []
        calculation_frame_max == None
        calculation_frame_min == None
        frame_peaks = []

    # Update Data
    current_time = current_time + interval_between_data_points


