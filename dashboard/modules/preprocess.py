import mne
import numpy as np

TARGET_FS = 256  # Hz

def preprocess_edf(input_path, output_path):
    raw = mne.io.read_raw_edf(input_path, preload=True, verbose=False)

    # Resample to 256 Hz
    raw.resample(TARGET_FS)

    # # Optional: basic cleanup
    # raw.filter(l_freq=0.5, h_freq=40.0)

    # # Save preprocessed data
    # raw.save(output_path, overwrite=True)

    # don't need?
    # # Get data in µV
    # data = raw.get_data() * 1e6  # V -> µV
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