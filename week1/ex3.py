from machine import Pin, I2C
from ssd1306 import SSD1306_I2C

button_sw1 = Pin(7, Pin.IN, Pin.PULL_UP)
button_sw2 = Pin(9, Pin.IN, Pin.PULL_UP)
button_sw3 = Pin(8, Pin.IN, Pin.PULL_UP)

i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_width = 128
oled_height = 64
oled = SSD1306_I2C(oled_width, oled_height, i2c)
oled.fill(0)

x = 0
y = oled_height // 2



while True:
    
    x += 1
    if x == oled_width :
        x = 0  

    

    if button_sw1.value() == 0:
        y -= 1
        if y < 0:
            y = 0
    if button_sw2.value() == 0:
        y += 1
        if y >= oled_height:
            y = oled_height - 1 
    

 
    if not button_sw3():
        oled.fill(0)
        x = 0
        y = oled_height // 2
        

    oled.pixel(x,y,1)
    oled.show()