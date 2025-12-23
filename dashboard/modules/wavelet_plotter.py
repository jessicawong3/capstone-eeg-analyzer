from PyQt5 import QtWidgets
import pyqtgraph as pg
import numpy as np
from collections import deque

class WaveletPlot(QtWidgets.QWidget):
    def __init__(self, levels=["A5","D5","D4","D3","D2","D1"], buffer_size=600):
        super().__init__()

        self.levels = levels
        self.buffer_size = buffer_size
        
        # Ring buffer for each band
        self.data = {lvl: deque([0]*buffer_size, maxlen=buffer_size) for lvl in levels}

        # Plot widget
        self.plot = pg.PlotWidget(title="Wavelet Coefficients (DWT)")
        self.img = pg.ImageItem()
        self.plot.addItem(self.img)
        self.plot.setAspectLocked(False)
        self.plot.getAxis("left").setTicks([list(enumerate(levels))])

        # Generate a colormap: one color per frequency band
        colors = [
            (255, 0, 0, 255),      # Red
            (0, 255, 0, 255),      # Green
            (0, 0, 255, 255),      # Blue
            (255, 255, 0, 255),    # Yellow
            (255, 0, 255, 255),    # Magenta
            (0, 255, 255, 255)     # Cyan
        ]
        # Repeat colors if more levels than colors
        colors = [colors[i % len(colors)] for i in range(len(levels))]
        positions = np.linspace(0, 1, len(colors))
        self.cmap = pg.ColorMap(positions, colors)
        self.img.setLookupTable(self.cmap.getLookupTable(0.0, 1.0, 256))

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.plot)
        self.setLayout(layout)

    def update_coeffs(self, coeffs):
        """
        coeffs = {"A5": val, "D5": val, ...}
        """
        for lvl in self.levels:
            self.data[lvl].append(abs(coeffs.get(lvl,0)))

        matrix = np.array([self.data[lvl] for lvl in self.levels])
        matrix = np.flipud(matrix)  # high freq at bottom
        self.img.setImage(matrix)

        # adjust limits
        self.img.setLevels([0, matrix.max() or 1])
