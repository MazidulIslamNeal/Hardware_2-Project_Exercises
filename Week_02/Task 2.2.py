import micropython

from filefifo import Filefifo

previous_slop_sign = 0

data = Filefifo(10, name='sample_data/capture_250Hz_01.txt')

interval_between_data_points = 4  # as 250 samples is in one second so there will be one sample in every 4 ms.

current_time = 0

max_sample = -9999999  # a big negative number
min_sample = 9999999  # a big positive number

for _ in range(501):  # 1 second conatins 250 samples so 2 second conatins 500 samples
    sample = data.get()

    if max_sample < sample:
        max_sample = sample
    if min_sample > sample:
        min_sample = sample

print("MAX: ", max_sample)
print("MIN: ", min_sample)

data = Filefifo(10, name='sample_data/capture_250Hz_01.txt')

for _ in range(2500):  # 1 second conatins 250 samples so 2 second conatins 500 samples
    removed_minimum = data.get() - min_sample
    scaled_sample = 100 * removed_minimum / (max_sample - min_sample)
    print(scaled_sample)
