import pyqtgraph as pg
import numpy as np
import pywt


class WaveletPlot(pg.GraphicsLayoutWidget):
    def __init__(self, n_levels=6, window_len=300):
        super().__init__(title="Discrete Wavelet Transform |Coefficients|")

        # self.setBackground("w")

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
        dwt_labels = ["d3", "d4H", "d4L", "d5", "d6", "d7", "d8"]
        ticks = [(i, dwt_labels[i]) for i in range(n_levels)]
        self.plot.getAxis("left").setTicks([ticks])

        self.plot.setLimits(
            xMin=0, xMax=window_len,
            yMin=-1, yMax=n_levels
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


    def update_from_fpga(self, fpga_coefficients):
        """
        Update wavelet plot with pre-computed DWT coefficients from FPGA.
        Coefficients are already computed, just need to be displayed.
        
        fpga_coefficients: 1D array of 6 DWT coefficient values
                          (one from each 5-second window)
        """
        
        # Shift left (time scroll) by 1 column
        self.coeff_img = np.roll(self.coeff_img, -1, axis=1)
        
        # Insert new column of coefficients on the right
        # If we have 6 coefficients and n_levels, map them accordingly
        # Assuming fpga_coefficients contains one value per level
        n_coeffs = min(len(fpga_coefficients), self.n_levels)
        for i in range(n_coeffs):
            self.coeff_img[i, -1] = abs(fpga_coefficients[i])
        
        # Update image with the scrolled display
        self.img.setImage(
            self.coeff_img,
            autoLevels=True
        )



    def load_signal(self, signal, wavelet="db4", level=6, precomputed=False):
        """
        signal: 1D EEG array (for local DWT computation) OR pre-computed DWT coefficients from FPGA
        precomputed: If True, signal is already DWT coefficients (shape n_levels x n_time)
                     If False, signal is raw EEG data and we compute DWT
        """

        if precomputed:
            # Signal is already DWT coefficients, just reshape and display
            # Reshape from flat array to (n_levels, n_time)
            n_levels = self.n_levels
            n_time = len(signal) // n_levels if len(signal) % n_levels == 0 else len(signal)
            
            img = signal[:n_levels * n_time].reshape(n_levels, n_time)
            print(f"Using pre-computed DWT coefficients: {img.shape}")
        else:
            # Compute DWT from raw signal
            # Compute DWT (real data mode)
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








# TEST
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
