#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gpiozero import Button
from threading import Lock
import time

# Pin configuration
TACH_PIN = 13       # Fan's tachometer output pin
PULSE = 2       # Noctua fans puts out two pluses per revolution
WAIT_TIME = 1   # [s] Time to wait between each refresh

# Setup
fan_tach = Button(TACH_PIN)

# Setup variables
pulse_count = 0
pulse_lock = Lock()

# Calculate pulse frequency and RPM
def pressed():
    global pulse_count
    with pulse_lock:
        pulse_count += 1

fan_tach.when_activated = pressed

try:
    last = time.monotonic()
    while True:
        time.sleep(WAIT_TIME)   # Detect every second
        now = time.monotonic()
        interval = now - last
        last = now
        with pulse_lock:
            pulses = pulse_count
            pulse_count = 0
        rpm = 0.0
        if interval > 0:
            rpm = (pulses / PULSE) * (60 / interval)
        print(f"{rpm:.0f} RPM")

except KeyboardInterrupt:   # trap a CTRL+C keyboard interrupt
    exit()
