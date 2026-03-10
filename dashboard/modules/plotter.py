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

    # --- Real Data mode ---
    def update_plot(self, times, data):
        """Render a full static EEG trace (real data mode)."""
        self._synthetic_mode = False
        self.plot_widget.enableAutoRange()
        self.curve.setData(times, data)


    # --- Synthetic mode ---
    def start_synthetic(self, fs: int = 256):
        """Switch to rolling-window live display at the given sample rate."""
        self._synthetic_fs = fs
        self._synthetic_times = np.arange(LIVE_WINDOW) / fs
        self._synthetic_buffer = np.zeros(LIVE_WINDOW)
        self._synthetic_mode = True
        self.plot_widget.enableAutoRange()


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
