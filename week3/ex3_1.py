from machine import Pin
from fifo import Fifo
from time import sleep_ms
from led import Led


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
#led_pin = Pin(22, mode=Pin.OUT)

led = Led(22,brightness=50)

rot = Encoder(10, 11)

brightness = 0
led_on = False
prev_toggle_button_state = True  # Assuming the button is initially not pressed

selection_delay = 0

while True:
    if selection_delay>0:
        selection_delay = selection_delay -1
    
    if rot.fifo.has_data():
        rotation = rot.fifo.get()
        if led_on:
            brightness += rotation*5
            if brightness < 0:
                brightness = 0
            elif brightness > 100:
                brightness = 100
            led.brightness(brightness)

    current_toggle_button_state = toggle_button.value()
    if current_toggle_button_state != prev_toggle_button_state and current_toggle_button_state == 0 and selection_delay <=0:
        selection_delay = 10
        # Toggle button was pressed
        led_on = not led_on
        if led_on:
            brightness = .5  # Turn on LED with initial brightness
        else:
            brightness = 0  # Turn off LED
        if(led_on):
            led.brightness(brightness)
            led.on()
        else:
            led.off()
                

    prev_toggle_button_state = current_toggle_button_state

