#! /usr/bin/env python3
from gpiozero import PWMOutputDevice
from enum import Enum
import os
import time
import signal
import sys

# The Noctua PWM control actually wants 25 kHz (kilo!), see page 6 on:
# https://noctua.at/pub/media/wysiwyg/Noctua_PWM_specifications_white_paper.pdf

# Notes on PWM frequency:
# - The Noctua spec calls for ~25 kHz, but the lgpio backend on this hardware
#   rejects 11–25 kHz and only accepts up to 10 kHz.
# - At 10 kHz, the fan tended to clamp to a higher minimum RPM (less low‑speed control).
# - At 100 Hz, the fan can reach a lower stable speed (≈5% duty yielded ~450 RPM),
#   even though very low duty cycles may stutter.
# - We choose 100 Hz here to preserve low‑RPM control; increase if you prefer
#   smoother PWM at the expense of a higher minimum speed.
PWM_FREQ_HZ = 100       # [Hz] PWM frequency (default backend rate)

PWM_PIN = 12            # BCM pin used to drive PWM fan
TACH_PIN = 13           # Reserved for tach read on the other node
WAIT_TIME = 1           # [s] Time to wait between each refresh

OFF_TEMP = 40           # [°C] temperature below which to stop the fan
MIN_TEMP = 45           # [°C] temperature above which to start the fan
MAX_TEMP = 70           # [°C] temperature at which to operate at max fan speed

FAN_PROFILE_PATH = "/etc/fan-control/profile"

class FanProfile(Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"

    @classmethod
    def from_string(cls, value: str):
        normalized = value.strip().lower()
        mapping = {
            "linear": cls.LINEAR,
            "ease_in": cls.EASE_IN,
            "ease_out": cls.EASE_OUT,
            "ease_in_out": cls.EASE_IN_OUT,
        }
        return mapping.get(normalized)


def getCpuTemperature():
    with open('/sys/class/thermal/thermal_zone0/temp') as f:
        return float(f.read()) / 1000


def clamp_speed(speed: float) -> float:
    return max(0.0, min(1.0, speed))


def normalize_temperature(temperature: float) -> float:
    if MAX_TEMP <= MIN_TEMP:
        return 1.0 if temperature >= MAX_TEMP else 0.0
    if temperature <= MIN_TEMP:
        return 0.0
    if temperature >= MAX_TEMP:
        return 1.0
    return (temperature - MIN_TEMP) / (MAX_TEMP - MIN_TEMP)


def linear_curve(progress: float) -> float:
    return progress


def ease_in_curve(progress: float) -> float:
    return progress * progress * progress


def ease_out_curve(progress: float) -> float:
    return (progress - 1) * (progress - 1) * (progress - 1) + 1


def ease_in_out_curve(progress: float) -> float:
    if progress < 0.5:
        return 0.5 * ease_in_curve(2 * progress)
    return 0.5 * ease_out_curve(2 * progress - 1) + 0.5


def select_curve(profile: FanProfile):
    if profile == FanProfile.EASE_IN:
        return ease_in_curve
    if profile == FanProfile.EASE_OUT:
        return ease_out_curve
    if profile == FanProfile.EASE_IN_OUT:
        return ease_in_out_curve
    return linear_curve


def get_profile_override():
    try:
        with open(FAN_PROFILE_PATH) as handle:
            raw = handle.read().strip()
    except FileNotFoundError:
        return None
    except OSError as exc:
        print(
            f"{FAN_PROFILE_PATH}: read failed ({exc}); defaulting to linear.",
            file=sys.stderr,
        )
        return None

    if not raw:
        return None

    profile = FanProfile.from_string(raw)
    if profile is None:
        print(
            f"{FAN_PROFILE_PATH}: unknown profile '{raw}'; defaulting to linear.",
            file=sys.stderr,
        )
    return profile


def get_lgpio_factory():
    try:
        from gpiozero.pins.lgpio import LGPIOFactory
    except Exception as exc:
        print(
            f"LGPIOFactory unavailable ({exc}); falling back to default pin factory.",
            file=sys.stderr,
        )
        return None

    try:
        return LGPIOFactory()
    except Exception as exc:
        print(
            f"Failed to initialize LGPIOFactory ({exc}); using default pin factory.",
            file=sys.stderr,
        )
        return None


def ensure_working_dir():
    try:
        cwd = os.getcwd()
    except FileNotFoundError:
        cwd = None

    if not cwd or not os.path.isdir(cwd):
        fallback = "/tmp"
        print(
            f"Working directory missing; lgpio needs a writable directory to create "
            f"its .lgd-nfy* pipe. Falling back to {fallback}.",
            file=sys.stderr,
        )
        os.chdir(fallback)
        return

    if not os.access(cwd, os.W_OK):
        fallback = "/tmp"
        print(
            f"Working directory '{cwd}' is not writable; lgpio needs a writable "
            f"directory to create its .lgd-nfy* pipe. Consider running as root, "
            f"adjusting permissions, or setting a WorkingDirectory= in systemd. "
            f"Falling back to {fallback}.",
            file=sys.stderr,
        )
        os.chdir(fallback)


def pwm_for_temperature(temperature: float, curve_fn) -> float:
    if temperature <= OFF_TEMP:
        return 0.0
    if temperature < MIN_TEMP:
        return 0.0
    progress = normalize_temperature(temperature)
    return clamp_speed(curve_fn(progress))


def handleFanSpeed(fan: PWMOutputDevice, temperature: float, curve_fn):
    speed = pwm_for_temperature(temperature, curve_fn)
    if speed <= 0.0:
        fan.off()
    else:
        fan.value = speed


try:
    signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
    ensure_working_dir()
    pin_factory = get_lgpio_factory()
    fan = PWMOutputDevice(PWM_PIN, pin_factory=pin_factory)
    try:
        fan.frequency = PWM_FREQ_HZ
    except Exception as exc:
        print(
            f"Failed to set PWM frequency to {PWM_FREQ_HZ}Hz: {exc}. Using default.",
            file=sys.stderr,
        )
    profile = get_profile_override() or FanProfile.LINEAR
    curve_fn = select_curve(profile)
    while True:
        handleFanSpeed(fan, getCpuTemperature(), curve_fn)
        time.sleep(WAIT_TIME)

except KeyboardInterrupt:
    exit()
