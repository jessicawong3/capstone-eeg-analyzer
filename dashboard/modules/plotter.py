from PyQt5 import QtWidgets
import pyqtgraph as pg

class EEGPlot(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.plot_widget = pg.PlotWidget(title="EEG Signal")

        # # Custom background
        # self.plot_widget.setBackground('#ffffff')  # White background
        # # Plot line style
        # pen = pg.mkPen(color='blue', width=2)  # Blue line

        # self.curve = self.plot_widget.plot([], [], pen=pen)
        self.curve = self.plot_widget.plot([], [])

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

    def update_plot(self, times, data):
        self.curve.setData(times, data)
        self.plot_widget.enableAutoRange()




# TEST
# import numpy as np
# import pyqtgraph as pg
# from PyQt5 import QtWidgets

# class EEGPlot(QtWidgets.QWidget):
#     def __init__(self, window_len=300, fs=100):
#         super().__init__()

#         self.window_len = window_len
#         self.fs = fs

#         # Rolling buffer
#         self.data = np.zeros(window_len)
#         self.time = np.arange(window_len) / fs

#         self.plot_widget = pg.PlotWidget(title="EEG Signal")
#         self.plot_widget.setLabel("bottom", "Time", units="s")
#         self.plot_widget.setLabel("left", "Amplitude")

#         self.curve = self.plot_widget.plot(self.time, self.data)

#         # Lock view
#         self.plot_widget.setLimits(
#             xMin=0,
#             xMax=self.time[-1]
#         )

#         layout = QtWidgets.QVBoxLayout()
#         layout.addWidget(self.plot_widget)
#         self.setLayout(layout)

#     def update_sample(self, value):
#         """Scroll EEG left and append one new sample"""

#         self.data = np.roll(self.data, -1)
#         self.data[-1] = value

#         self.curve.setData(self.time, self.data)
