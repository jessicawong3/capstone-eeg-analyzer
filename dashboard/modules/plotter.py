from PyQt5 import QtWidgets
import pyqtgraph as pg
import numpy as np

# Number of samples to show in the rolling live window
LIVE_WINDOW = 512


class EEGPlot(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.plot_widget = pg.PlotWidget(title="EEG Signal")
        self.plot_widget.setLabel("bottom", "Time", units="s")
        self.plot_widget.setLabel("left", "Voltage", units="V")

        self.curve = self.plot_widget.plot([], []) #, pen=pg.mkPen(color="#4f46e5", width=1))

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        # Rolling buffer for synthetic mode
        self._synthetic_buffer = np.zeros(LIVE_WINDOW)
        self._synthetic_fs = 256 # adjust for MCU Hz !!!
        self._synthetic_times = np.arange(LIVE_WINDOW) / self._synthetic_fs
        self._synthetic_mode = False
        self._last_redraw = 0.0  # timestamp of last setData call
        self._current_stage = None  # Track which stage is currently being displayed
        
        # Real data rolling mode
        self._real_data_buffer = np.zeros(LIVE_WINDOW)
        self._real_data_times = np.arange(LIVE_WINDOW) / 256  # will be updated
        self._real_data_fs = 256  # will be set when data is loaded

    # --- Real Data mode ---
    def update_plot(self, times, data):
        """Render a full static EEG trace (real data mode)."""
        self._synthetic_mode = False
        self.plot_widget.enableAutoRange()
        self.curve.setData(times, data)

    def start_real_data_rolling(self, times: np.ndarray, data: np.ndarray, fs: int = 256, resume: bool = False):
        """Switch to rolling-window display for real data playback.
        
        Args:
            times: Full array of time values
            data: Full array of EEG data
            fs: Sampling frequency in Hz
            resume: If True, continue from current position. If False, restart from beginning.
        """
        self._synthetic_mode = False
        self._real_data_fs = fs
        self._real_data_times = np.arange(LIVE_WINDOW) / fs
        
        # Store the full data
        self._full_data = data
        self._full_times = times
        
        # Only reset buffer and index if not resuming
        if not resume or not hasattr(self, '_data_index'):
            self._real_data_buffer = np.full(LIVE_WINDOW, np.nan)
            self._data_index = 0  # Current position in the full dataset
        
        self.plot_widget.enableAutoRange()
        self.curve.setData(self._real_data_times, self._real_data_buffer)

    def append_real_data_chunk(self, chunk_size: int):
        """Load the next chunk of real data into the rolling buffer.
        
        Args:
            chunk_size: Number of samples to advance
            
        Returns:
            True if more data is available, False if at the end
        """
        if not hasattr(self, '_full_data'):
            return False
            
        # Check if we've reached the end
        if self._data_index >= len(self._full_data):
            return False
        
        # Get the next chunk
        end_idx = min(self._data_index + chunk_size, len(self._full_data))
        chunk = self._full_data[self._data_index:end_idx]
        actual_chunk_size = len(chunk)
        
        # Shift buffer and add new data
        self._real_data_buffer = np.roll(self._real_data_buffer, -actual_chunk_size)
        self._real_data_buffer[-actual_chunk_size:] = chunk
        self.curve.setData(self._real_data_times, self._real_data_buffer)
        
        self._data_index += actual_chunk_size
        
        # Return True if there's more data
        return self._data_index < len(self._full_data)


    # --- Synthetic mode ---
    def start_synthetic(self, fs: int = 256, stage: str = None):
        """Switch to rolling-window live display at the given sample rate.
        
        If stage is different from the current stage, resets the buffer.
        If stage is the same, continues with existing buffer.
        """
        # Only reset buffer if stage changed or first time
        if stage != self._current_stage:
            self._synthetic_buffer = np.full(LIVE_WINDOW, np.nan)  # Initialize with NaN to hide zeros
            self._current_stage = stage
        
        self._synthetic_fs = fs
        self._synthetic_times = np.arange(LIVE_WINDOW) / fs
        self._synthetic_mode = True
        self.plot_widget.enableAutoRange()
        self.curve.setData(self._synthetic_times, self._synthetic_buffer)  # Clear display


    def append_chunk(self, chunk: np.ndarray):
        """Shift a numpy array of samples into the rolling buffer and redraw once."""
        if not self._synthetic_mode:
            return
        n = len(chunk)
        self._synthetic_buffer = np.roll(self._synthetic_buffer, -n)
        self._synthetic_buffer[-n:] = chunk
        self.curve.setData(self._synthetic_times, self._synthetic_buffer)


    def stop_synthetic(self):
        """Exit synthetic mode (keeps last frame visible)."""
        self._synthetic_mode = False
