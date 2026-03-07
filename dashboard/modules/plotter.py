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

        # Rolling buffer for live mode
        self._live_buffer = np.zeros(LIVE_WINDOW)
        self._live_fs = 256 # adjust for MCU Hz !!!
        self._live_times = np.arange(LIVE_WINDOW) / self._live_fs
        self._live_mode = False


    # --- Offline mode ---
    def update_plot(self, times, data):
        """Render a full static EEG trace (offline mode)."""
        self._live_mode = False
        self.plot_widget.enableAutoRange()
        self.curve.setData(times, data)


    # --- Live mode ---
    def start_live(self, fs: int = 1000):
        """Switch to rolling-window live display at the given sample rate."""
        self._live_fs = fs
        self._live_times = np.arange(LIVE_WINDOW) / fs
        self._live_buffer = np.zeros(LIVE_WINDOW)
        self._live_mode = True
        self.plot_widget.enableAutoRange()


    def append_sample(self, voltage: float):
        """Shift one new sample into the rolling buffer and redraw."""
        if not self._live_mode:
            return
        self._live_buffer = np.roll(self._live_buffer, -1)
        self._live_buffer[-1] = voltage
        self.curve.setData(self._live_times, self._live_buffer)


    def stop_live(self):
        """Exit live mode (keeps last frame visible)."""
        self._live_mode = False
