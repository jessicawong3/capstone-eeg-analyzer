import pyqtgraph as pg
import numpy as np
import pywt


import numpy as np
import pyqtgraph as pg
from PyQt5 import QtGui

class WaveletPlot(pg.GraphicsLayoutWidget):
    def __init__(self, n_levels=7, window_len=6, sample_spacing=5): 
        super().__init__(title="Discrete Wavelet Transform |Coefficients|")

        self.n_levels = n_levels
        self.window_len = window_len
        self.sample_spacing = sample_spacing # each sample = 5 seconds
        self.total_time = window_len * sample_spacing

        self.coeff_img = np.zeros((n_levels, window_len))

        self.plot = self.addPlot()
        self.plot.setLabel("bottom", "Time", units="s")
        self.plot.setLabel("left", "DWT Level")
        
        # Invert Y so d3 is at the top
        self.plot.invertY(True)

        self.img = pg.ImageItem()
        self.plot.addItem(self.img)

        # Scale x-axis by sample_spacing so 6 samples = 30 seconds
        # (scaleX, shearY, shearX, scaleY, translateX, translateY)
        tr = QtGui.QTransform()
        tr.scale(self.sample_spacing, 1) 
        self.img.setTransform(tr)
        # -------------------------------

        cmap = pg.colormap.get("viridis")
        self.img.setColorMap(cmap)

        # Axis labeling
        dwt_labels = ["d3", "d4L", "d4H", "d5", "d6", "d7", "d8"]
        ticks = [(i, label) for i, label in enumerate(dwt_labels)]
        self.plot.getAxis("left").setTicks([ticks])

        # Set the view range to match our scaled time
        self.plot.setRange(xRange=(0, self.total_time), yRange=(0, n_levels), padding=0)
        self.plot.setLimits(xMin=0, xMax=self.total_time, yMin=0, yMax=n_levels)
        

    def update_from_fpga(self, fpga_coefficients):
        # Ensure data is a numpy array and absolute
        data_abs = np.abs(np.array(fpga_coefficients))

        # Force 2D if input was 1D
        if data_abs.ndim == 1:
            # Assuming if 1D, one level per row for a single time point
            data_abs = data_abs.reshape(-1, 1)

        n_new_points = data_abs.shape[1]
        
        # Roll buffer (left shift)
        self.coeff_img = np.roll(self.coeff_img, -n_new_points, axis=1)
        
        # Insert new data at the end
        n_levels_to_update = min(data_abs.shape[0], self.n_levels)
        self.coeff_img[:n_levels_to_update, -n_new_points:] = data_abs[:n_levels_to_update, :]

        self.img.setImage(self.coeff_img.T, autoLevels=True)


    def reset_plot(self):
        # Reset the internal data buffer
        self.coeff_img = np.zeros((self.n_levels, self.window_len))
        
        # Push zeroed data (autoLevels=False to prevent colormap from 'stretching' a zero-array into a single bright colour)
        self.img.setImage(self.coeff_img.T, autoLevels=False, levels=[0, 1])

        # Explicitly set ViewBox state (prevents axes from collapsing if AutoRange was active)
        vb = self.plot.getViewBox()
        vb.setRange(
            xRange=(0, self.window_len * 5), 
            yRange=(0, self.n_levels), 
            padding=0
        )
        
        # Re-apply the ticks
        dwt_labels = ["d3", "d4L", "d4H", "d5", "d6", "d7", "d8"]
        ticks = [(i, dwt_labels[i]) for i in range(self.n_levels)]
        self.plot.getAxis("left").setTicks([ticks])

        # Force a GUI refresh
        self.plot.update()