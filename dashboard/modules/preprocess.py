from __future__ import annotations

import mne
import numpy as np

TARGET_FS = 256  # Hz


# --- For FPGA --- #
def preprocess_edf(input_path, output_path):
    raw = mne.io.read_raw_edf(input_path, preload=True, verbose=False)

    # Resample to 256 Hz  # TODO: Reorder/redo this elsewhere if necessary
    raw.resample(TARGET_FS)

    data = raw.get_data()

    # TODO: Jenny's preprocessing steps here
    selected_channel_data = None

    # TODO: Simran's quantizations steps here with x1000 data
    quantized = quantization_function(selected_channel_data * 1000)

    # Export quantized data
    quantized.tofile(output_path)

    return output_path


# TODO: Replace with Simran's quantization function
def quantization_function(data, out_path):
    quantized = None
    return quantized



# --- For MCU --- #
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
            # print(f"Parsed raw token '{raw_token}' to int: {raw_int}")
        else:
            # print(f"Raw token '{raw_token}' is not a digit.")
            return None

        # 2. cast to uint16
        as_uint16 = np.uint16(raw_int)
        # print(f"Cast raw token '{raw_token}' to uint16: {as_uint16}")

        # 3. undo quantization
        dequantized = signed_fp_to_decimal_float(1, 14, as_uint16)

        # 4. divide by 1000 to get volts
        voltage = dequantized / 1000.0

        # print(f"Parsed token '{raw_token}' to voltage: {voltage} V")
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
