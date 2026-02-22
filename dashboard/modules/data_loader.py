import pandas as pd
import numpy as np
import mne


def load_eeg_data(filepath):
    raw = mne.io.read_raw_edf(filepath, preload=True)
    data, times = raw[:1]  # First channel
    return data[0], times


def load_hypnogram_data(filepath):
    """Load hypnogram data from EDF file and extract sleep stage annotations"""
    try:
        # Read annotations directly (more reliable for hypnogram files)
        annotations = mne.read_annotations(filepath)
        
        # Extract onset times and descriptions
        onset_times = annotations.onset
        descriptions = annotations.description
        durations = annotations.duration
        
        # Convert stage descriptions to standardized format
        sleep_stages = []
        for desc in descriptions:
            # Common hypnogram stage mappings
            stage_map = {
                'Sleep stage W': 'Awake',
                'Sleep stage 1': 'N1', 
                'Sleep stage 2': 'N2',
                'Sleep stage 3': 'N3',
                'Sleep stage 4': 'N3',  # N4 is often combined with N3
                'Sleep stage R': 'REM',
                'Sleep stage ?': 'Unknown',
                'Movement time': 'Movement',
                'W': 'Awake',
                'N1': 'N1',
                'N2': 'N2', 
                'N3': 'N3',
                'N4': 'N3',
                'R': 'REM',
                'REM': 'REM'
            }
            
            # Try to map the stage, default to original description if not found
            mapped_stage = stage_map.get(str(desc), str(desc))
            sleep_stages.append(mapped_stage)
        
        return onset_times, sleep_stages, durations
        
    except Exception as e:
        print(f"Error loading hypnogram: {e}")
        return None, None, None


def get_sleep_stage_at_time(hypno_data, time_point):
    """Get the sleep stage at a specific time point"""
    if hypno_data is None:
        return "Unknown"
    
    onset_times, sleep_stages, durations = hypno_data
    
    for i, onset in enumerate(onset_times):
        if onset <= time_point < onset + durations[i]:
            return sleep_stages[i]
    
    return "Unknown"


def suggest_hypnogram_file(eeg_filepath):
    """Suggest potential hypnogram file paths based on EEG file naming patterns"""
    import os
    
    eeg_dir = os.path.dirname(eeg_filepath)
    eeg_basename = os.path.basename(eeg_filepath)
    eeg_name_without_ext = os.path.splitext(eeg_basename)[0]
    
    # Common hypnogram naming patterns
    suggestions = []
    
    # Pattern 1: Replace "PSG" with "Hypnogram" (SC4591G0-PSG.edf -> SC4591GY-Hypnogram.edf)
    if "PSG" in eeg_name_without_ext:
        hypno_name = eeg_name_without_ext.replace("PSG", "Hypnogram").replace("G0", "GY") + ".edf"
        suggestions.append(os.path.join(eeg_dir, hypno_name))

    # Pattern 2: Add "-Hypnogram" suffix (SC4591G0.edf -> SC4591G0-Hypnogram.edf)
    hypno_name = eeg_name_without_ext + "-Hypnogram.edf"
    suggestions.append(os.path.join(eeg_dir, hypno_name))

    # Pattern 3: Replace subject ID pattern with Y suffix (SC4591G0 -> SC4591GY)
    import re
    match = re.search(r'(\w+)G0', eeg_name_without_ext)
    if match:
        base = match.group(1)
        hypno_name = base + "GY-Hypnogram.edf"
        suggestions.append(os.path.join(eeg_dir, hypno_name))
    
    # Return only suggestions that actually exist
    existing_suggestions = []
    for suggestion in suggestions:
        if os.path.exists(suggestion):
            existing_suggestions.append(suggestion)
    
    return existing_suggestions


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
