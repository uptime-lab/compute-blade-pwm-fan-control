# Compute Blade PWM Fan Control

Simple fan control and tach read scripts for the Compute Blade fan unit.

[Fan Unit Documentation](https://docs.computeblade.com/fan-unit)

## Install GPIO Zero

### apt

GPIO Zero is packaged in the apt repositories of Raspberry Pi OS, Debian and Ubuntu. It is also available on [PyPI](https://pypi.org/project/gpiozero/).

```bash
sudo apt update
sudo apt install python3-gpiozero
```

### pip

If you’re using another operating system on your Raspberry Pi, you may need to use pip to install GPIO Zero instead. Install pip using [get-pip](https://pip.pypa.io/en/stable/installing/) and then type:

```bash
sudo pip3 install gpiozero
```

## Usage

### Scripts

- `fan_control.py`: Drives PWM on GPIO12 and reads CPU temperature to set speed.
  - Profiles: `linear`, `ease_in`, `ease_out`, `ease_in_out`.
  - Profile file: `/etc/fan-control/profile` (single word).
  - Must be run as root for GPIO permissions.
- `read_fan_speed.py`: Reads tach pulses on GPIO13 and prints RPM.

### Fan Unit Connections

- J1 is the control node (only J1 can drive PWM). It can also read the tach signal.
- J2 can read tach signals, but cannot control PWM.

### Profile File

The fan control script supports some fan easing curves. Create the profile file with a single word inside:

```bash
sudo mkdir -p /etc/fan-control
echo ease_out | sudo tee /etc/fan-control/profile
```

Valid profiles:

| Profile       | Behavior                                               |
| ------------- | ------------------------------------------------------ |
| `linear` 🔹   | Speed increases linearly with temperature              |
| `ease_in`     | Starts slow, ramps faster at higher temps              |
| `ease_out`    | Ramps quickly, then levels off                         |
| `ease_in_out` | Slow at low temps, faster in the middle, smooth finish |

🔹 Default fan profile when not set

## Notes

- GPIO13 is reserved for tach reads on the other node; PWM control uses GPIO12.
