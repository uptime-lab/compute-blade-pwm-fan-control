#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from gpiozero import Button
import time

# Pin configuration
TACH_PIN = 13       # Fan's tachometer output pin
PULSE = 2       # Noctua fans puts out two pluses per revolution
WAIT_TIME = 1   # [s] Time to wait between each refresh

# Setup
fan_tach = Button(TACH_PIN)

# Setup variables
t = time.time()
rpm = 0

# Caculate pulse frequency and RPM
def pressed():
    global t
    global rpm

    dt = time.time() - t
    if dt < 0.005:
        return  # Reject spuriously short pulses

    freq = 1 / dt
    rpm = (freq / PULSE) * 60
    t = time.time()

fan_tach.when_activated = pressed

try:
    while True:
        print("%.f RPM" % rpm)
        rpm = 0
        time.sleep(WAIT_TIME)   # Detect every second

except KeyboardInterrupt:   # trap a CTRL+C keyboard interrupt
    exit()
