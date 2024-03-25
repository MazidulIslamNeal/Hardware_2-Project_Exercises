from machine import Pin
import ssd1306

# Initialize OLED display
WIDTH = 128
HEIGHT = 64
i2c = machine.I2C(1, scl=machine.Pin(15), sda=machine.Pin(14), freq=400000)
oled = ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c)
button1 = Pin(9, Pin.IN, Pin.PULL_UP)
button2 = Pin(7, Pin.IN, Pin.PULL_UP)

# Define initial UFO position
ufo_x = WIDTH // 2
ufo_y = HEIGHT - 10

# Function to move UFO left
def move_right():
    global ufo_x
    if ufo_x > 0:
        ufo_x -= 1

# Function to move UFO right
def move_left():
    global ufo_x
    if ufo_x < WIDTH - 8*3:
        ufo_x += 1

# Main loop
while True:
    # Clear the display
    oled.fill(0)
    
    # Draw UFO
    oled.text('<=>', ufo_x, ufo_y)
    
    # Show on OLED
    oled.show()
    
    # Check button presses
    if button1.value() == 0:  # SW0 pressed
        move_left()
    if button2.value() == 0:  # SW2 pressed
        move_right()

