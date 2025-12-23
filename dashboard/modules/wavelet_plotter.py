import pyqtgraph as pg
import numpy as np
import pywt


class WaveletPlot(pg.GraphicsLayoutWidget):
    def __init__(self, n_levels=6, window_len=300):
        super().__init__(title="Discrete Wavelet Transform |Coefficients|")

        self.n_levels = n_levels
        self.window_len = window_len

        # Matrix: rows = levels, cols = time
        self.coeff_img = np.zeros((n_levels, window_len))

        # Plot
        self.plot = self.addPlot()
        self.plot.setLabel("bottom", "Time")
        self.plot.setLabel("left", "DWT Level")
        self.plot.invertY(True)  # Level 1 at bottom like reference

        # Image item
        self.img = pg.ImageItem()
        self.plot.addItem(self.img)

        # Colormap (similar to MATLAB jet/parula)
        cmap = pg.colormap.get("viridis")
        self.img.setColorMap(cmap)

        # Scale axes
        # self.img.setRect(0, 0, self.window_len, self.n_levels)


        # Y-axis ticks (levels)
        ticks = [(i, f"L{i+1}") for i in range(n_levels)]
        self.plot.getAxis("left").setTicks([ticks])

        self.plot.setLimits(
            xMin=0, xMax=window_len,
            yMin=0, yMax=n_levels
        )

    def update_coeffs(self, coeffs):
        """
        coeffs example:
        {
            "D1": v,
            "D2": v,
            ...
        }
        """

        # Shift left (time scroll)
        self.coeff_img = np.roll(self.coeff_img, -1, axis=1)

        # Insert new column (absolute coefficients)
        for i in range(self.n_levels):
            key = f"D{i+1}"
            self.coeff_img[i, -1] = abs(coeffs.get(key, 0.0))

        # Update image
        self.img.setImage(
            self.coeff_img,
            autoLevels=True
        )

    def load_signal(self, signal, wavelet="db4", level=6):
        """
        signal: 1D EEG array (same as EEGPlot)
        """

        # Compute DWT (offline)
        coeffs = pywt.wavedec(signal, wavelet, level=level)

        # coeffs = [A6, D6, D5, ..., D1]
        details = coeffs[1:]  # drop approximation

        n_levels = len(details)
        n_time = min(len(d) for d in details)

        img = np.zeros((n_levels, n_time))

        for i, d in enumerate(details):
            img[i, :] = np.log10(np.abs(d[:n_time]) + 1e-6)

        self.coeff_img = img
        self.img.setImage(img, autoLevels=True)








# from PyQt5 import QtWidgets
# import pyqtgraph as pg
# import numpy as np
# from collections import deque

# class WaveletPlot(QtWidgets.QWidget):
#     def __init__(self, levels=["A5","D5","D4","D3","D2","D1"], buffer_size=600):
#         super().__init__()

#         self.levels = levels
#         self.buffer_size = buffer_size
        
#         # Ring buffer for each band
#         self.data = {lvl: deque([0]*buffer_size, maxlen=buffer_size) for lvl in levels}

#         # Plot widget
#         self.plot = pg.PlotWidget(title="Wavelet Coefficients (DWT)")
#         self.img = pg.ImageItem()
#         self.plot.addItem(self.img)
#         self.plot.setAspectLocked(False)
#         self.plot.getAxis("left").setTicks([list(enumerate(levels))])

#         # Generate a colormap: one color per frequency band
#         colors = [
#             (255, 0, 0, 255),      # Red
#             (0, 255, 0, 255),      # Green
#             (0, 0, 255, 255),      # Blue
#             (255, 255, 0, 255),    # Yellow
#             (255, 0, 255, 255),    # Magenta
#             (0, 255, 255, 255)     # Cyan
#         ]
#         # Repeat colors if more levels than colors
#         colors = [colors[i % len(colors)] for i in range(len(levels))]
#         positions = np.linspace(0, 1, len(colors))
#         self.cmap = pg.ColorMap(positions, colors)
#         self.img.setLookupTable(self.cmap.getLookupTable(0.0, 1.0, 256))

#         layout = QtWidgets.QVBoxLayout()
#         layout.addWidget(self.plot)
#         self.setLayout(layout)

#     def update_coeffs(self, coeffs):
#         """
#         coeffs = {"A5": val, "D5": val, ...}
#         """
#         for lvl in self.levels:
#             self.data[lvl].append(abs(coeffs.get(lvl,0)))

#         matrix = np.array([self.data[lvl] for lvl in self.levels])
#         matrix = np.flipud(matrix)  # high freq at bottom
#         self.img.setImage(matrix)

#         # adjust limits
#         self.img.setLevels([0, matrix.max() or 1])
