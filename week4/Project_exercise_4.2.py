from filefifo import Filefifo
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import time

# function to scale values to a specific range
def scale_value(value, min_value, max_value, new_min_value, new_max_value):
    scaled_value = int(((value - min_value) / (max_value - min_value)) * (new_max_value - new_min_value) + new_min_value)
    return scaled_value


# initializing filefifo (signal source)
data = Filefifo(10, name="capture03_250Hz.txt")
# scanning signal for values
signals = []
for i in range(2500):
    signals.append(data.get())
    
# separate temporary array for easy appending to cut array
temporary_array = []
cut_array = []
# cut array is an array made of arrays that have 250 samples each
# to enumerate is to get both the count and the value of the count, instead of just value of the count
for i, val in enumerate(signals):
    temporary_array.append(val)
    # if next array is the 250th sample, cut the array and append it to cut_array as another piece
    if (i+1) % 250 == 0:
        cut_array.append(temporary_array)
        # emptying temporary array for the next cut
        temporary_array = []


scaled_array = []
temporary_array = []
# use the first min and max numbers to scale the next group's data
for i, val in enumerate(cut_array):
    # scales only if there is a next group that can be scaled
    if i < len(cut_array)-1:
        # getting max and min values
        # first max and min values
        old_max_num = max(cut_array[i])
        old_min_num = min(cut_array[i])
        # max and min values from the next group
        next_max_num = max(cut_array[i+1])
        next_min_num = min(cut_array[i+1])
        # scaling the next group using the first group
        for i in cut_array[i+1]:
            scaled_value = scale_value(i, next_min_num, next_max_num, old_min_num, old_max_num)
            temporary_array.append(scaled_value)
        # putting the scaled value to the main array, emptying temp array
        scaled_array.append(temporary_array)
        temporary_array = []


# getting the averages of every 5 samples
average_array = []
average_buffer = 0
for i in scaled_array:
    # for every value within one piece of the scaled array:
    for i, val in enumerate(i):
        # putting values in the average_buffer to calculate average
        average_buffer += val
        # if 5th sample is reached, calculate the average and empty the average_buffer
        if (i+1) % 5 == 0:
            average_array.append(average_buffer / 5)
            average_buffer = 0

# numbers that the averaged values have to be re-scaled to in order to fit the screen height of 64px(-1)
new_max_num = 63
new_min_num = 0

# scaling averaged numbers to new scaled numbers so they can be plotted on the screen
max_num = max(average_array)
min_num = min(average_array)
# final array made for screen-safe numbers
rescaled_array = []
for i in average_array:
    scaled_value = scale_value(i, min_num, max_num, new_min_num, new_max_num)
    rescaled_array.append(scaled_value)

# initializing screen
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)


# plotting the values
temporary_array = []
# using the rescaled values for y values, plotting everything to the site
for x_id, value in enumerate(rescaled_array):
    print(value)
    temporary_array.append(value)
    if x_id >= oled_width:
       del temporary_array[0]
       oled.fill(0)
       for i, value2 in enumerate(temporary_array):
           oled.pixel(i, 63-value2, 1)
 
    oled.pixel(x_id, 63-rescaled_array[x_id], 1)
    oled.show()
