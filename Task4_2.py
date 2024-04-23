import machine
import ssd1306
from filefifo import Filefifo


WIDTH = 128
HEIGHT = 64
i2c = machine.I2C(1, scl=machine.Pin(15), sda=machine.Pin(14), freq=400000)
oled = ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)

file_fifo = Filefifo(10, name='sample_data/capture_250Hz_01.txt')  


scale_min = None
scale_max = None
window_size = 250  # number of sample

while True:
    oled.fill(0)

    samples = []
    for _ in range(window_size):
        sample = file_fifo.get()
        if sample is not None:
            samples.append(sample)

    if len(samples) == window_size:
        
        current_min = min(samples)
        current_max = max(samples)

        if scale_min is None or current_min < scale_min:
            scale_min = current_min
        if scale_max is None or current_max < scale_max:
            scale_max = current_max

        for i in range(0, len(samples), 5):  
            avg_sample = sum(samples[i:i+5]) / 5
            scaled_sample = int((avg_sample - scale_min) / (scale_max - scale_min) * (HEIGHT - 1))
            if scaled_sample < 0:
                scaled_sample = 0
            elif scaled_sample > HEIGHT - 1:
                scaled_sample = HEIGHT - 1
            oled.pixel(i // 5, HEIGHT - 1 - scaled_sample, 1)

        oled.show()

