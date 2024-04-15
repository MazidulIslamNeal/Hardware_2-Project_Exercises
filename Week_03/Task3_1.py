from machine import Pin
from fifo import Fifo
from time import sleep_ms

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

toggle_button = Pin(12, mode=Pin.IN, pull=Pin.PULL_UP)
led = Pin(22, mode=Pin.OUT)

rot = Encoder(10, 11)

brightness = 0
led_on = False
prev_toggle_button_state = True  # Assuming the button is initially not pressed

while True:
    if rot.fifo.has_data() and led_on:
        rotation = rot.fifo.get()
        brightness += rotation
        if brightness < 0:
            brightness = 0
        elif brightness > 10:
            brightness = 10

    current_toggle_button_state = toggle_button.value()
    if current_toggle_button_state != prev_toggle_button_state and current_toggle_button_state == 0:
        # Toggle button was pressed
        led_on = not led_on
        if led_on:
            brightness = 1  # Turn on LED with initial brightness
        else:
            brightness = 0  # Turn off LED

    prev_toggle_button_state = current_toggle_button_state

    if led_on:
        for _ in range(brightness):
            led.on()
            sleep_ms(1)
            led.off()
            sleep_ms(10 - brightness)

    sleep_ms(10)

