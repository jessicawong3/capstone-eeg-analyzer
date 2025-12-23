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
