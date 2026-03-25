from __future__ import annotations

import mne
import numpy as np
import re
from pathlib import Path

TARGET_FS = 256  # Hz


# --- For FPGA --- #
def preprocess_edf(input_path, output_path):
    """
    Preprocess EDF file and save as .npz with epochs and labels.
    """
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

    # Extract labels from hypnogram file
    labels = _extract_labels_from_hypnogram(input_path, n_epochs)
    
    # Ensure labels match the number of epochs
    if labels is not None and len(labels) != n_epochs:
        print(f"Warning: Label count ({len(labels)}) doesn't match epoch count ({n_epochs}). "
              f"Truncating or padding labels.")
        if len(labels) < n_epochs:
            # Pad with -1 (unknown) if we have fewer labels
            labels = np.pad(labels, (0, n_epochs - len(labels)), constant_values=-1)
        else:
            # Truncate if we have more labels
            labels = labels[:n_epochs]
    elif labels is None:
        # Default to 0 (unknown) if we couldn't extract labels
        labels = np.zeros(n_epochs, dtype=np.int64)
    
    # Ensure labels are int64 to match demo format
    labels = np.array(labels, dtype=np.int64)
    
    # Convert output_path to .npz if needed
    output_path_obj = Path(output_path)
    if output_path_obj.suffix != ".npz":
        output_path = str(output_path_obj.with_suffix(".npz"))
    
    # Save as .npz file with epochs and labels
    np.savez(output_path, epochs=channel_epochs, labels=labels)
    print(f"Saved preprocessed data to {output_path}")
    print(f"  Epochs shape: {channel_epochs.shape}")
    print(f"  Labels shape: {labels.shape}")

    return output_path


def _extract_labels_from_hypnogram(eeg_path, n_epochs):
    """
    Extract sleep stage labels from the hypnogram EDF file corresponding to the EEG file.
    """
    eeg_path = Path(eeg_path)
    eeg_dir = eeg_path.parent
    eeg_name = eeg_path.stem
    
    # Try to find the corresponding hypnogram file
    hypno_candidates = []
    
    # Pattern 1: Replace "PSG" with "Hypnogram" (SC4591G0-PSG.edf -> SC4591GY-Hypnogram.edf)
    if "PSG" in eeg_name:
        hypno_name = eeg_name.replace("PSG", "Hypnogram").replace("G0", "GY") + ".edf"
        hypno_candidates.append(eeg_dir / hypno_name)
    
    # Pattern 2: Add "-Hypnogram" suffix (SC4591G0.edf -> SC4591G0-Hypnogram.edf)
    hypno_name = eeg_name + "-Hypnogram.edf"
    hypno_candidates.append(eeg_dir / hypno_name)
    
    # Pattern 3: Replace subject ID pattern with Y suffix (SC4591G0 -> SC4591GY)
    match = re.search(r'(\w+)G0', eeg_name)
    if match:
        base = match.group(1)
        hypno_name = base + "GY-Hypnogram.edf"
        hypno_candidates.append(eeg_dir / hypno_name)
    
    # Try to read from the first existing hypnogram file
    for hypno_path in hypno_candidates:
        if hypno_path.exists():
            return _extract_labels_from_hypnogram_file(str(hypno_path), n_epochs)
    
    print(f"Warning: Could not find hypnogram file for {eeg_path}")
    return None


def _extract_labels_from_hypnogram_file(hypno_path, n_epochs):
    """
    Extract sleep stage labels from a hypnogram EDF file.
    """
    try:
        # Read annotations from the hypnogram file
        annotations = mne.read_annotations(hypno_path)
        
        # Stage mapping to numeric labels
        stage_map = {
            'Sleep stage W': 0,
            'Sleep stage 1': 1,
            'Sleep stage 2': 2,
            'Sleep stage 3': 3,
            'Sleep stage 4': 3,  # N4 combined with N3
            'Sleep stage R': 4,
            'Sleep stage ?': -1,
            'W': 0,
            'N1': 1,
            'N2': 2,
            'N3': 3,
            'N4': 3,
            'R': 4,
            'REM': 4
        }
        
        # Extract labels for each 30-second epoch
        labels = []
        for i in range(n_epochs):
            epoch_start = i * 30  # Each epoch is 30 seconds
            epoch_end = (i + 1) * 30
            
            # Find annotation that covers this epoch
            label = -1  # Default to unknown
            for onset, duration, description in zip(
                annotations.onset, annotations.duration, annotations.description
            ):
                # Check if this annotation overlaps with the epoch
                annot_end = onset + duration
                if onset <= epoch_start < annot_end or onset < epoch_end <= annot_end:
                    label = stage_map.get(str(description), -1)
                    break
            
            labels.append(label)
        
        labels = np.array(labels, dtype=np.int64)
        print(f"Extracted {len(labels)} labels from hypnogram")
        return labels
        
    except Exception as e:
        print(f"Error extracting labels from hypnogram {hypno_path}: {e}")
        return None


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
    print(f"Wavelet coefficient data for graph: {data[:, keep_idx]}")
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
