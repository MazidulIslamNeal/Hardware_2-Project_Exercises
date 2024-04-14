from machine import Pin
from fifo import Fifo
import ssd1306

# Initialize OLED display
WIDTH = 128
HEIGHT = 64
i2c = machine.I2C(1, scl=machine.Pin(15), sda=machine.Pin(14), freq=400000)
oled = ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)

# Define initial UFO position
ufo_x = 0
ufo_y = 0


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


def generate_led_status(led_number, is_selected, status):
    led_line = ""

    if is_selected:
        led_line += "["
    else:
        led_line += " "

    led_line += " LED{} - {}".format(led_number, " ON" if status else "OFF")

    if is_selected:
        led_line += " ]"

    return led_line


button = Pin(12, mode=Pin.IN, pull=Pin.PULL_UP)

led0 = Pin(22, Pin.OUT)
led1 = Pin(21, Pin.OUT)
led2 = Pin(20, Pin.OUT)

led_array = [led0, led1, led2]

rot = Encoder(10, 11)

selected = 0

led_status = [False, False, False]

selected_delay = 0

while True:
    if selected_delay > 0:
        selected_delay = selected_delay - 1

    # Clear the display
    oled.fill(0)

    for i in range(3):
        oled.text(generate_led_status(i + 1, i == selected, led_status[i]), 1, 1 + i * 12)

    # Show on OLED
    oled.show()

    if rot.fifo.has_data():
        rotation = rot.fifo.get()
        selected = selected + rotation
        if selected < 0:
            selected = 2
        if selected > 2:
            selected = 0

    if button.value() == 0 and selected_delay <= 0:
        selected_delay = 10
        led_status[selected] = not led_status[selected]
        if led_status[selected]:
            led_array[selected].on()
        else:
            led_array[selected].off()
