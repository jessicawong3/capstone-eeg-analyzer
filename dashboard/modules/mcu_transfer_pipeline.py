from __future__ import annotations

import serial
import serial.tools.list_ports
import numpy as np
import time

# Serial port settings
BAUD_RATE = 115200
DEFAULT_PORT = "/dev/tty.usbmodem11303"

# Command bytes to send to MCU for each sleep stage
STAGE_COMMANDS = {
    "Offline": b"0",
    "Awake":   b"W",
    "REM":     b"R",
    "N1":      b"1",
    "N2":      b"2",
    "N3":      b"3",
}

# --- FOR MOCK MCU ---
# Global variable to track current stage for mock mode
_current_mock_stage = "Awake"
# Stage-specific value ranges for mock data
STAGE_BASE_VALUES = {
    "Awake": {"base": 32000, "range": 2000},   # Higher, more variable
    "REM": {"base": 25000, "range": 1500},     # Medium-high
    "N1": {"base": 22000, "range": 1200},      # Medium
    "N2": {"base": 18000, "range": 1000},      # Lower
    "N3": {"base": 15000, "range": 800},       # Lowest, more regular
    "Offline": {"base": 8000, "range": 500},   # Very low baseline
}


def open_serial(port: str = DEFAULT_PORT):
    # Open and return a serial connection to the MCU
    return serial.Serial(port, baudrate=BAUD_RATE, timeout=1)


def send_stage_command(ser: serial.Serial, stage: str):
    print(f"sending stage: {stage}")
    # Send the single-byte command for a given sleep stage to the MCU
    cmd = STAGE_COMMANDS.get(stage)
    if cmd is None:
        raise ValueError(f"Unknown stage '{stage}'. Valid stages: {list(STAGE_COMMANDS.keys())}")
    
    # Update global stage for mock mode
    global _current_mock_stage
    _current_mock_stage = stage
    
    ser.write(cmd)


def read_one_sample(ser: serial.Serial):
    # Read one raw token from the MCU
    # Read until /r and return the token string.

    # print("Reading sample?")
    try:
        line = ser.read_until(b"\r").decode("ascii", errors="ignore").strip()
        # line = ser.readline()
        # print(line)
        # print(f"Type: {type(line)}")
        f = open('serial.txt', 'a')
        data = str(line)
        f.write(data)
        f.close()

        # print(line)
        return line if line else None
    except serial.SerialException:
        return None
    

# Mock mcu output (0 to 2^16 - 1) — sleeps to simulate real MCU sample rate
def mock_read_one_sample():
    time.sleep(1 / 256)   # simulate 256 Hz
    
    # Get stage-specific base value and range
    stage_config = STAGE_BASE_VALUES.get(_current_mock_stage, STAGE_BASE_VALUES["Awake"])
    base = stage_config["base"]
    noise_range = stage_config["range"]
    
    # Generate value with stage-specific characteristics
    value = base + np.random.randint(-noise_range, noise_range + 1)
    # Clamp to valid 16-bit range
    value = np.clip(value, 0, 2**16 - 1)
    
    line = str(int(value))
    return line

