import micropython

from filefifo import Filefifo

previous_slop_sign = 0

data = Filefifo(10, name='sample_data/capture_250Hz_01.txt')

previous_datapoint = None

peak_count = 0
slope = 0

interval_between_data_points = 4  # as 250 samples is in one second so there will be one sample in every 4 ms.

current_time = 0

peaks = []

peak_store_count = 0

for _ in range(25931):
    sample = data.get()
    if previous_datapoint != None:
        slope = (sample - previous_datapoint)  # we do not need the exact slope, we just need the sign. that is why I am not deviding with x values

        if previous_slop_sign >= 0 and slope < 0:
            peak_count = peak_count + 1
            
            if(len(peaks)<3):
                peaks.append((current_time, sample))

    # Update Data
    current_time = current_time + interval_between_data_points
    previous_datapoint = sample
    previous_slop_sign = slope

peak_frequency = 1 / ((peaks[1][0] - peaks[0][0]) / 1000)

print("Total peak count: ", peak_count, "\n")

print("First three peaks: ")

for peak in peaks:
    print(f"{peak[0]} ms : {peak[1]}")
    

print("\nSignal Frequency: ", peak_frequency, "Hz")
