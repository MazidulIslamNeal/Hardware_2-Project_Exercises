from machine import Pin
from fifo import Fifo
import ssd1306

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


def generate_led_status(led_number, is_selected, status):
    led_line = ""  # blank string

    if is_selected:
        led_line += "["
    else:
        led_line += " "

    status_string = ""

    if status:
        status_string = " ON"
    else:
        status_string = "OFF"

    inner_string = " LED{} - {}"

    led_line += inner_string.format(led_number, status_string)

    if is_selected:
        led_line += " ]"

    return led_line


button = Pin(12, mode=Pin.IN, pull=Pin.PULL_UP)

led0 = Pin(22, Pin.OUT)

led1 = Pin(21, Pin.OUT)

led2 = Pin(20, Pin.OUT)

led0.off()
led1.off()
led2.off()

led_array = [led0, led1, led2]

rot = Encoder(10, 11)

selected = 0

led_status = [False, False, False]

selected_delay = 0

while True:
    if selected_delay > 0:
        selected_delay = selected_delay - 1

    # ---- Only for print nothing else
    # Clear the display
    oled.fill(0)

    for i in range(3):
        oled.text(generate_led_status(i + 1, i == selected, led_status[i]), 0, i * 18)

    # Show on OLED
    oled.show()
    # ------ Only for Print

    # ---- Only for changing selection internally. In the print section it will be used to show the selection in LED
    if rot.fifo.has_data():
        rotation = rot.fifo.get()
        selected = selected + rotation
        if selected < 0:
            # selected = 2
            selected = 0
        if selected > 2:
            # selected = 0
            selected = 2
    # ---- Only for changing selection internally.

    # ---- Only for turning on the LED of and on and Changing the Led_status OFF and ON for display in next cycle
    if button.value() == 0 and selected_delay <= 0:
        selected_delay = 10
        led_status[selected] = not led_status[selected]
        if led_status[selected]:
            led_array[selected].on()
        else:
            led_array[selected].off()

