from __future__ import annotations

import mne
import numpy as np

TARGET_FS = 256  # Hz


# --- For FPGA --- #
def preprocess_edf(input_path, output_path):
    raw = mne.io.read_raw_edf(input_path, preload=True, verbose=False)
    eeg_channel = "EEG Fpz-Cz"

    # Resample to 256 Hz
    raw.resample(sfreq=TARGET_FS, npad='auto', verbose=False)
    raw.filter(l_freq=0.5, h_freq=None, picks=[eeg_channel], verbose=False)

    data = raw.copy().pick_channels([eeg_channel]).get_data()[0]  # Get the data for the selected channel

    # preprocessing steps
    selected_channel_data = np.array(data)  

    # quantizations steps with x1000 data
    #quantized = quantization_function(1, 14, selected_channel_data * 1000)

    # Split into 30-second epochs (256 Hz * 30 seconds = 7680 samples per epoch)
    samples_per_epoch = 256 * 30  # 7680 samples
    n_epochs = len(selected_channel_data) // samples_per_epoch
    
    # Reshape to (n_epochs, samples_per_epoch) - same format as quantized_epochs.npy
    channel_epochs = selected_channel_data[:n_epochs * samples_per_epoch].reshape(n_epochs, samples_per_epoch)

    # Export quantized epochs as .npy file
    np.save(output_path, channel_epochs)  # Save the raw epochs; quantization done on the FPGA side

    return output_path


# want to call like quantization_function(int_bits=1, fraction_bits=14, signed_dec=unquntized_data)
#MIGHT HAVE TO CHANGE IF JEREMY'S FPGA USES A DIFFERENT QUANTIZATION SCHEME
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
#MIGHT HAVE TO CHANGE TO MATCH JEREMY'S FPGA 
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



# FOR NPY DEMO FILES
def parse_npy_sample(npy_voltage):
  # Convert a single raw npy voltage to a real voltage value.
  # 1. Cast to uint16
  # 2. Undo quantization
  # 3. Divide by 1000 to get volts

  try:

      # 1. cast to uint16
      as_uint16 = np.uint16(npy_voltage)

      # 2. undo quantization
      dequantized = signed_fp_to_decimal_float(1, 14, as_uint16)

      # 3. divide by 1000 to get volts
      voltage = dequantized / 1000.0

      print(f"Parsed voltage: {voltage}")

      return voltage
  except (ValueError, TypeError):
      return None

def get_graph_data_from_data(data):
    """extract 1 data point of eeg data from every 5 seconds windows"""
    keep_idx = [0, 5*32, 10*32, 15*32, 20*32, 25*32]
    return data[:, keep_idx]

def get_pred_data_from_data(data):
    """get prediction and confidence in that prediction"""
    """ | prediction (0-4) | confidence in Awake | confidence in N1 | confidence in N2 | confidence in N3 | confidence in REM | """
    return [int(data[0]), data[int(data[0])+1]]



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
