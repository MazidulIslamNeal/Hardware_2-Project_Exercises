import micropython

from filefifo import Filefifo

previous_slop_sign = 0

data = Filefifo(10, name='sample_data/capture_250Hz_01.txt')

previous_datapoint = None

peak_count = 0
slope = 0

interval_between_data_points = 4  # as 250 samples is in one second so there will be one sample in every 4 ms.

current_time = 0

peak1_time = 0
peak2_time = 0
peak3_time = 0

peak1_sample = 0
peak2_sample = 0
peak3_sample = 0

peak_store_count = 0

for _ in range(2572):
    sample = data.get()
    if previous_datapoint != None:
        slope = (
                    sample - previous_datapoint)  # we do not need the exact slope, we just need the sign. that is why I am not deviding with x values

        if previous_slop_sign > 0 and slope < 0:
            peak_count = peak_count + 1
            if peak_store_count == 0:
                peak1_time = current_time
                peak1_sample = sample
                peak_store_count = 1
            elif peak_store_count == 1:
                peak2_time = current_time
                peak2_sample = sample
                peak_store_count = 2
            elif peak_store_count == 2:
                peak3_time = current_time
                peak3_sample = sample
                peak_store_count = 3

    # Update Data
    current_time = current_time + interval_between_data_points
    previous_datapoint = sample
    previous_slop_sign = slope

peak_frequency = 1 / ((peak2_time - peak1_time) / 1000)

print("Total peak count: ", peak_count, "\n")

print("First three peaks: ")

print(peak1_time, " ms : ", peak1_sample)
print(peak2_time, " ms : ", peak2_sample)
print(peak3_time, " ms : ", peak3_sample, "\n")

print("Signal Frequency: ", peak_frequency, "Hz")
