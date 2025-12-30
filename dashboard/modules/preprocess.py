import mne

TARGET_FS = 256  # Hz

def preprocess_edf(input_path, output_path):
    raw = mne.io.read_raw_edf(input_path, preload=True, verbose=False)

    # Resample to 256 Hz
    raw.resample(TARGET_FS)

    # Optional: basic cleanup
    raw.filter(l_freq=0.5, h_freq=40.0)

    # Save preprocessed data
    raw.save(output_path, overwrite=True)

    return output_path
