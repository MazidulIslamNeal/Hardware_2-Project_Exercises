import time
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C

i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)

def clear_screen():
    oled.fill(0)
    oled.show()

def draw_text(lines):
    clear_screen()
    for i, line in enumerate(lines):
        oled.text(line, 0, i * 8)
    oled.show()

lines = []  

while True:
    user_input = input("Enter text: ")
    lines.append(user_input)
    draw_text(lines)
    #print(len(lines)*8)
    if len(lines) * 8 >= oled_height:
        del lines[0]
    
    time.sleep(0.1) 