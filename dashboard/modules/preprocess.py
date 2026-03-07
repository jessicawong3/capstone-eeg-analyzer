from __future__ import annotations

import mne
import numpy as np

TARGET_FS = 256  # Hz


def preprocess_edf(input_path, output_path):
    raw = mne.io.read_raw_edf(input_path, preload=True, verbose=False)

    # Resample to 256 Hz
    raw.resample(TARGET_FS)

    data = raw.get_data()

    # Export FPGA binary
    export_fpga_bin(data, output_path)

    return output_path


def export_fpga_bin(data_uv, out_path):
    """
    data_uv: shape (channels, samples) OR (samples,)
             values in microvolts (float)
    out_path: path to .bin file
    """
    # Ensure 2D [channels, samples]
    if data_uv.ndim == 1:
        data_uv = data_uv[np.newaxis, :]

    # Convert to int16 fixed-point
    data_i16 = np.clip(data_uv, -32768, 32767).astype("<i2")

    # Interleave samples: [s0_ch0, s0_ch1, ..., s1_ch0, ...]
    interleaved = data_i16.T
    interleaved.tofile(out_path)


# 1. MCU input comes in *1000, quantized, number (in format: "####/r")
# 2. Convert to uint16_t
# 3. Undo quantization, then /1000 to get "real" values
def preprocess_voltages(input_path, output_path):
    with open(input_path, 'r') as f:
        content = f.read()

    # Parse the input
    samples = []
    for line in content.split('/r'):
        try:
            value = int(line.strip())
            samples.append(value)
        except ValueError:
            continue

    # Convert to uint16_t
    samples = np.array(samples, dtype=np.uint16)

    # Undo quantization
    real_values = samples.astype(np.float32) / 1000.0

    # Export FPGA binary
    export_fpga_bin(real_values, output_path)

    return output_path


def parse_mcu_sample(raw_token: str):
    # Convert a single raw MCU token to a real voltage value.
    # 1. Parse the token string to an integer
    # 2. Cast to uint16
    # 3. Undo quantization
    # 4. Divide by 1000 to get volts
    print("Parsing raw token")

    try:
        # 1. parse to integer
        if raw_token.isdigit():
            raw_int = int(raw_token.replace("\r", "").strip())
            print(f"Parsed raw token '{raw_token}' to int: {raw_int}")
        else:
            print(f"Raw token '{raw_token}' is not a digit.")
            return None

        # 2. cast to uint16
        as_uint16 = np.uint16(raw_int)
        print(f"Cast raw token '{raw_token}' to uint16: {as_uint16}")

        # 3. undo quantization
        dequantized = signed_fp_to_decimal_float(1, 14, as_uint16)

        # 4. divide by 1000 to get volts
        voltage = dequantized / 1000.0

        print(f"Parsed token '{raw_token}' to voltage: {voltage} V")
        return voltage
    except (ValueError, TypeError):
        print(f"Failed to parse token '{raw_token}'")
        return None


# Unquantization function
def signed_fp_to_decimal_float(int_bits, fraction_bits, signed_fp_num):
  # this only works if the fp number is 16 bits. I'm going to type cast it to be sure it is.
  num_16_int = np.uint16(signed_fp_num)

  #if negative, apply 2's complement
  sign = (num_16_int & 0x8000) >> 15
  if (sign == 1):
    #apply 2's complement
    num_16_int = (~num_16_int + 1) & 0xFFFF

  #apply scaling
  to_return = num_16_int/(2**fraction_bits)
  if (sign == 1):
    to_return = -to_return

  return to_return
  # RETURNS NP.FLOAT64 TYPE
