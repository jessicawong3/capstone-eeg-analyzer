from __future__ import annotations

import serial
import serial.tools.list_ports

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


def open_serial(port: str = DEFAULT_PORT):
    # Open and return a serial connection to the MCU
    return serial.Serial(port, baudrate=BAUD_RATE, timeout=1)


def send_stage_command(ser: serial.Serial, stage: str):
    print(f"sending stage: {stage}")
    # Send the single-byte command for a given sleep stage to the MCU
    cmd = STAGE_COMMANDS.get(stage)
    if cmd is None:
        raise ValueError(f"Unknown stage '{stage}'. Valid stages: {list(STAGE_COMMANDS.keys())}")
    
    ser.write(cmd)


def read_one_sample(ser: serial.Serial):
    # Read one raw token from the MCU
    # Read until /r and return the token string.

    print("Reading sample?")
    try:
        line = ser.read_until(b"\r").decode("ascii", errors="ignore").strip()
        # line = ser.readline()
        print(line)
        print(f"Type: {type(line)}")
        f = open('serial.txt', 'a')
        data = str(line)
        f.write(data)
        f.close()

        # print(line)
        return line if line else None
    except serial.SerialException:
        return None
    