from machine import Pin
from fifo import Fifo
import ssd1306
from filefifo import Filefifo

# Initialize OLED display
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


file_fifo = Filefifo(10, name='sample_data/capture_250Hz_01.txt')  # Note the capitalization change
data_list = []
while len(data_list) <= 1000:  # Read until you have 1000 values
    data_list.append(file_fifo.get())

min_value = min(data_list)
max_value = max(data_list)

rot = Encoder(10, 11)
window_start = 0

while True:
    if rot.fifo.has_data():
        rotation = rot.fifo.get()
        window_start += rotation * 50
        if window_start < 0:
            window_start = 0
        elif window_start > len(data_list) - 128:
            window_start = len(data_list) - 128

    window_end = window_start + 128
    window_data = data_list[window_start:window_end]

    # Clear the display
    oled.fill(0)

    # Display windowed data on OLED
    for i, value in enumerate(window_data):
        oled.text("Value {}: {}".format(window_start + i, value), 0, i * 10)

    oled.show()  # Update the OLED display
