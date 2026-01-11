import time
import board
import busio
import displayio
import terminalio
import neopixel
import keypad
import random
import rtc
import usb_hid
from adafruit_display_text import label
from adafruit_displayio_ssd1306 import SSD1306
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

"""
Configuring Hardware Setup
"""

#SCREEN
displayio.release_displays()
i2c = busio.I2C(scl=board.D1, sda=board.D0)
display_bus = displayio.I2CDisplay(i2c, device_address=0x3c)
display = SSD1306(display_bus, width=128, height=32)

#LED
PIXEL_PIN = board.D2
NUM_PIXELS = 1 
pixels = neopixel.NeoPixel(PIXEL_PIN, NUM_PIXELS, brightness=0.3, auto_write=False, pixel_order=neopixel.GRB)

#KEYPAD MATRIX 
# Cols: Pins 8,9,10,11 -> D7, D8, D9, D10
col_pins = (board.D7, board.D8, board.D9, board.D10)
# Rows: Pins 7,6,5,4   -> D6, D5, D4, D3
row_pins = (board.D6, board.D5, board.D4, board.D3)

km = keypad.KeyMatrix(row_pins, col_pins)

#USB KEYBOARD & CLOCK
kbd = Keyboard(usb_hid.devices)
r = rtc.RTC()

# Set default start time if power was lost (2025-01-01 12:00:00)
if r.datetime.tm_year < 2024:
    r.datetime = time.struct_time((2025, 1, 1, 12, 0, 0, 0, 1, -1))

"""
Helper Functions
"""
def show_text(line1, line2=""):
    # Clear screen
    splash = displayio.Group()
    display.root_group = splash
    
    # Draw Line 1
    text_1 = label.Label(terminalio.FONT, text=line1, color=0xFFFFFF, x=2, y=6)
    splash.append(text_1)
    
    # Draw Line 2
    if line2:
        text_2 = label.Label(terminalio.FONT, text=line2, color=0xFFFFFF, x=2, y=22)
        splash.append(text_2)

def set_led(color):
    pixels[0] = color
    pixels.show()

def get_keypress_blocking():
    # Stops everything until a key is pressed
    while True:
        event = km.events.get()
        if event and event.pressed:
            return event.key_number

def get_keypress_nonblocking():
    # Returns key immediately if pressed, else returns None
    event = km.events.get()
    if event and event.pressed:
        return event.key_number
    return None

"""
Functions for Mini-Games and Modes
"""

def play_memory_game():
    score = 0
    sequence = []
    
    show_text("Memory Game!", "Get ready...")
    time.sleep(1)
    
    while True:
        # Phase 1: Show Sequence
        show_text(f"Level {score + 1}", "Watch...")
        new_key = random.randint(0, 15)
        sequence.append(new_key)
        time.sleep(1)
        
        for step in sequence:
            show_text(f"KEY: {step}")
            set_led((0, 0, 255)) # Blue
            time.sleep(0.6)
            show_text("")
            set_led((0, 0, 0))
            time.sleep(0.2)
            
        # Phase 2: User Input
        show_text("Your Turn!")
        set_led((255, 255, 0)) # Yellow
        
        for expected_key in sequence:
            # Wait for user to press ANY key
            while True:
                user_key = get_keypress_nonblocking()
                if user_key is not None:
                    break
            
            # Check if correct
            if user_key != expected_key:
                set_led((255, 0, 0)) # Red
                show_text("GAME OVER", f"Score: {score}")
                time.sleep(3)
                return # Exit to menu
            
            # Correct feedback
            set_led((0, 255, 0)) # Green
            time.sleep(0.1)
            set_led((255, 255, 0)) # Back to Yellow
            
        score += 1
        set_led((0, 255, 0))
        show_text("Correct!")
        time.sleep(0.5)

def play_whack_a_mole():
    score = 0
    timeout = 2.0 # Gets faster!
    
    show_text("Whack-a-Mole!", "Hit the key!")
    time.sleep(1.5)
    
    while True:
        target_key = random.randint(0, 15)
        show_text(f"HIT: {target_key}", f"Score: {score}")
        set_led((255, 0, 255)) # Purple
        
        start_time = time.monotonic()
        hit = False
        
        # Loop for the duration of 'timeout'
        while (time.monotonic() - start_time) < timeout:
            key = get_keypress_nonblocking()
            if key is not None:
                if key == target_key:
                    hit = True
                    break 
                else:
                    set_led((255, 0, 0))
                    show_text("WRONG KEY!", f"Final: {score}")
                    time.sleep(2)
                    return
        
        if hit:
            score += 1
            set_led((0, 255, 0))
            time.sleep(0.2)
            timeout = max(0.5, timeout * 0.95) # Make it 5% faster
        else:
            set_led((255, 0, 0))
            show_text("TOO SLOW!", f"Final: {score}")
            time.sleep(2)
            return

def run_numpad():
    # Standard Numpad Map
    key_map = {
        0: Keycode.SEVEN, 1: Keycode.EIGHT, 2: Keycode.NINE, 3: Keycode.KEYPAD_FORWARD_SLASH,
        4: Keycode.FOUR,  5: Keycode.FIVE,  6: Keycode.SIX,  7: Keycode.KEYPAD_ASTERISK,
        8: Keycode.ONE,   9: Keycode.TWO,   10: Keycode.THREE, 11: Keycode.KEYPAD_MINUS,
        12: Keycode.ZERO, 13: Keycode.KEYPAD_PERIOD, 14: Keycode.ENTER, 15: Keycode.KEYPAD_PLUS
    }

    show_text("Numpad Mode", "Hold Key 0 Exit")
    set_led((255, 255, 255)) # White
    
    while True:
        event = km.events.get()
        if event:
            key = event.key_number
            if key in key_map:
                if event.pressed:
                    kbd.press(key_map[key])
                    # Exit check: Hold Key 0 for 2 seconds
                    if key == 0:
                        start_hold = time.monotonic()
                        while True:
                            if km.events.get(): # If released
                                kbd.release(key_map[key])
                                break
                            if time.monotonic() - start_hold > 2.0:
                                kbd.release_all()
                                return # Exit
                elif event.released:
                    kbd.release(key_map[key])

def set_time_manually():
    # Key 0/4: Hour +/-
    # Key 1/5: Min +/-
    # Key 3: Save
    t = r.datetime
    new_h = t.tm_hour
    new_m = t.tm_min
    
    while True:
        time_str = "{:02d}:{:02d}".format(new_h, new_m)
        show_text("SET TIME:", f"{time_str} (3=OK)")
        
        key = get_keypress_blocking()
        if key == 0: new_h = (new_h + 1) % 24
        elif key == 4: new_h = (new_h - 1) % 24
        elif key == 1: new_m = (new_m + 1) % 60
        elif key == 5: new_m = (new_m - 1) % 60
        elif key == 3: 
            r.datetime = time.struct_time((2025, 1, 1, new_h, new_m, 0, 0, 1, -1))
            return
        time.sleep(0.2)

"""
Main Loop
"""

last_update = 0
set_led((0, 255, 255)) # Cyan startup

while True:
    # 1. Update Clock (Once per second)
    now = time.monotonic()
    if now - last_update > 1.0:
        current_t = r.datetime
        time_str = "{:02d}:{:02d}:{:02d}".format(current_t.tm_hour, current_t.tm_min, current_t.tm_sec)
        # Show Menu Options on line 2
        show_text(f"TIME: {time_str}", "0:Mem 1:Mol 2:Num")
        last_update = now
    
    # 2. Check for Menu Selection
    key = get_keypress_nonblocking()
    if key is not None:
        if key == 0:
            play_memory_game()
        elif key == 1:
            play_whack_a_mole()
        elif key == 2:
            run_numpad()
        elif key == 15: # Bottom Right Key
            set_time_manually()
        
        # Reset Menu after app closes
        set_led((0, 255, 255)) 
        show_text("Loading...")
        time.sleep(0.5)
