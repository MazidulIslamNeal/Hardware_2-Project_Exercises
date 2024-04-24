from machine import Pin
from fifo import Fifo
import ssd1306
from filefifo import Filefifo

WIDTH = 128
HEIGHT = 64
i2c = machine.I2C(1, scl=machine.Pin(15), sda=machine.Pin(14), freq=400000)
oled = ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)

class Encoder:
    def __init__(self, rot_a, rot_b):
        self.a = Pin(rot_a, mode=Pin.IN, pull=Pin.PULL_UP)
        self.b = Pin(rot_b, mode=Pin.IN, pull=Pin.PULL_UP)
        self.fifo = Fifo(30, typecode='i')
        self.a.irq(handler=self.handler, trigger=Pin.IRQ_RISING, hard=True)

    def handler(self, pin):
        if self.b():
            self.fifo.put(-1)
        else:
            self.fifo.put(1)

file_fifo = Filefifo(10, name='sample_data/capture_250Hz_01.txt')  
data_list = []
while len(data_list) < 1000:  # Reading 1000 values
    data_list.append(file_fifo.get())

min_value = min(data_list)
max_value = max(data_list)

rot = Encoder(10, 11)
window_start = 0

while True:
    while rot.fifo.has_data(): #don't use if
        rotation = rot.fifo.get()
        window_start += rotation*50
        if window_start < 0:
            window_start = 0
        elif window_start > len(data_list) - 128:
            window_start = len(data_list) - 128
    
    window_end = window_start + 128
    window_data = data_list[window_start:window_end]
    # Clear the display
    oled.fill(0)
    
    for i in range(1, len(window_data)):
        y0 = int((window_data[i - 1] - min_value) / (max_value - min_value) * HEIGHT)
        y1 = int((window_data[i] - min_value) / (max_value - min_value) * HEIGHT)
        x0 = int((i - 1) / (len(window_data) - 1) * WIDTH)  # Calculate x-coordinate for point i-1
        x1 = int(i / (len(window_data) - 1) * WIDTH)        # Calculate x-coordinate for point i
        oled.line(x0, y0, x1, y1, 1)
        
    oled.show()
