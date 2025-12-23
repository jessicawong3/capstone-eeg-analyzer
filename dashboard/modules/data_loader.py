import pandas as pd
import numpy as np
import mne


def load_eeg_data(filepath):
    raw = mne.io.read_raw_edf(filepath, preload=True)
    data, times = raw[:1]  # First channel
    return data[0], times


def load_csv_data(filepath):
    """Load EEG CSV with columns: time, amplitude"""
    df = pd.read_csv(filepath)
    times = df.iloc[:, 0].values
    data = df.iloc[:, 1].values
    return data, times


# For quick testing, if no file exists:
if __name__ == "__main__":
    # Generates a fake sine wave EEG CSV
    import math
    t = np.linspace(0, 10, 1000)
    y = np.sin(2 * math.pi * 10 * t)  # 10 Hz wave
    pd.DataFrame({"time": t, "amplitude": y}).to_csv("../test_data/sample.csv", index=False)
