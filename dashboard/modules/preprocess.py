from __future__ import annotations

import mne
import numpy as np

TARGET_FS = 256  # Hz


# --- For FPGA --- #
def preprocess_edf(input_path, output_path):
    raw = mne.io.read_raw_edf(input_path, preload=True, verbose=False)
    eeg_channel = "EEG Fpz-Cz"

    # Resample to 256 Hz  # TODO: Reorder/redo this elsewhere if necessary
    raw.resample(sfreq=TARGET_FS, npad='auto', verbose=False)
    raw.filter(l_freq=0.5, h_freq=None, picks=[eeg_channel], verbose=False)

    data = raw.copy().pick_channels([eeg_channel]).get_data()[0]  # Get the data for the selected channel

    # TODO: Jenny's preprocessing steps here
    selected_channel_data = np.array(data)  

    # TODO: Simran's quantizations steps here with x1000 data
    quantized = quantization_function(1, 14, selected_channel_data * 1000)

    # Export quantized data
    quantized.tofile(output_path)

    return output_path


# TODO: Replace with Simran's quantization function
# want to call like quantization_function(int_bits=1, fraction_bits=14, signed_dec=unquntized_data)
def quantization_function(int_bits, fraction_bits, signed_dec):
    # scale it to get the quantized number
    signed_dec = np.asarray(signed_dec, dtype=np.float64)

    sign = signed_dec < 0
    magnitude = np.abs(signed_dec)
    quantized = np.uint16(magnitude*2**fraction_bits)
    # Apply two's complement where negative
    quantized = np.where(
        sign,
        (~quantized + 1) & 0xFFFF,
        quantized
    ).astype(np.uint16)

    return quantized
    #RETURN NP.UINT16



# --- For MCU --- #
def parse_mcu_sample(raw_token: str):
    # Convert a single raw MCU token to a real voltage value.
    # 1. Parse the token string to an integer
    # 2. Cast to uint16
    # 3. Undo quantization
    # 4. Divide by 1000 to get volts

    try:
        # 1. parse to integer — strip whitespace/carriage returns then convert
        raw_int = int(raw_token.strip())

        # 2. cast to uint16
        as_uint16 = np.uint16(raw_int)

        # 3. undo quantization
        dequantized = signed_fp_to_decimal_float(1, 14, as_uint16)

        # 4. divide by 1000 to get volts
        voltage = dequantized / 1000.0

        return voltage
    except (ValueError, TypeError):
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

# #   food for thought: code to read labels
# def map_stage(stage):
#     # PhysioNet scoring → AASM mapping
#     if stage in ['Sleep stage W']:
#         return 0  # Wake
#     if stage in ['Sleep stage 1', 'N1']:
#         return 1
#     if stage in ['Sleep stage 2', 'N2']:
#         return 2
#     if stage in ['Sleep stage 3', 'Sleep stage 4', 'N3']:
#         return 3
#     if stage in ['Sleep stage R']:
#         return 4  # REM
#     # if stage in ['Sleep stage ?']:
#     #     return 5  # not scored
#     return -1  # Unknown / ignore

# def get_labels(input_path, output_path):
#     raw = mne.io.read_raw_edf(input_path, preload=True, verbose=False)
#     annot = mne.read_annotations(input_path)
#     raw.set_annotations(annot, emit_warning=False)

#     events, event_ids = mne.events_from_annotations(raw=raw, chunk_duration=30)
#     labels = []

#     event_ids_reverse = {v: str(k) for k, v in event_ids.items()}

#     for ev in events:
#         event_code = ev[2]
#         stage_str = event_ids_reverse[event_code]
#         label = map_stage(stage_str)
#         labels.append(label)

#     labels = np.array(labels)

#     return labels
