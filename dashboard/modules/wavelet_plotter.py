import pyqtgraph as pg
import numpy as np
import pywt


class WaveletPlot(pg.GraphicsLayoutWidget):
    def __init__(self, n_levels=7, window_len=6): # window_len is 6 samples
        super().__init__(title="Discrete Wavelet Transform |Coefficients|")

        self.n_levels = n_levels
        self.window_len = window_len

        self.coeff_img = np.zeros((n_levels, window_len))

        self.plot = self.addPlot()
        self.plot.setLabel("bottom", "Time", units="s") # Added 's' for seconds
        self.plot.setLabel("left", "DWT Level")
        self.plot.invertY(True)

        self.img = pg.ImageItem()
        
        # --- THE FIX ---
        # Scale the X-axis by 5. Now 6 samples = 30 units.
        self.img.setScale(5) 
        # ---------------
        
        self.plot.addItem(self.img)

        cmap = pg.colormap.get("turbo")
        self.img.setColorMap(cmap)

        dwt_labels = ["d3", "d4L", "d4H", "d5", "d6", "d7", "d8"]
        ticks = [(i, dwt_labels[i]) for i in range(n_levels)]
        self.plot.getAxis("left").setTicks([ticks])

        # Update limits to 30 (6 samples * 5 seconds)
        self.plot.setLimits(
            xMin=0, xMax=window_len * 5,
            yMin=-1, yMax=n_levels
        )
        self.plot.setXRange(0, window_len * 5)

# class WaveletPlot(pg.GraphicsLayoutWidget):
#     def __init__(self, n_levels=7, window_len=6):
#         super().__init__(title="Discrete Wavelet Transform |Coefficients|")

#         self.n_levels = n_levels
#         self.window_len = window_len

#         # Matrix: rows = levels, cols = time
#         self.coeff_img = np.zeros((n_levels, window_len))

#         # Plot
#         self.plot = self.addPlot()
#         self.plot.setLabel("bottom", "Time")
#         self.plot.setLabel("left", "DWT Level")
#         self.plot.invertY(True)

#         # Image item
#         self.img = pg.ImageItem()
#         self.plot.addItem(self.img)

#         # Colormap (similar to MATLAB jet/parula)
#         cmap = pg.colormap.get("viridis")
#         self.img.setColorMap(cmap)

#         # Scale axes
#         # self.img.setRect(0, 0, self.window_len, self.n_levels)

#         # Y-axis ticks (levels)
#         dwt_labels = ["d3", "d4L", "d4H", "d5", "d6", "d7", "d8"]
#         ticks = [(i, dwt_labels[i]) for i in range(n_levels)]
#         self.plot.getAxis("left").setTicks([ticks])

#         self.plot.setLimits(
#             xMin=0, xMax=window_len,
#             yMin=-1, yMax=n_levels
#         )


    def update_from_fpga(self, fpga_coefficients):
        # 1. Ensure NumPy array and take absolute value
        data_abs = np.abs(np.array(fpga_coefficients))

        # 2. Force 2D if input was 1D
        if data_abs.ndim == 1:
            # Assuming if 1D, one level per row for a single time point
            data_abs = data_abs.reshape(-1, 1)

        n_new_points = data_abs.shape[1]
        
        # 3. Roll buffer
        self.coeff_img = np.roll(self.coeff_img, -n_new_points, axis=1)
        
        # 4. Insert data
        n_levels_to_update = min(data_abs.shape[0], self.n_levels)
        self.coeff_img[:n_levels_to_update, -n_new_points:] = data_abs[:n_levels_to_update, :]

        # 5. Display (transpose for pyqtgraph ImageItem, autoLevels=True stretched colormap)
        self.img.setImage(self.coeff_img.T, autoLevels=True)


    def clear(self):
        # 1. Reset the internal data buffer
        self.coeff_img = np.zeros((self.n_levels, self.window_len))
        
        # 2. Push zeroed data. Use autoLevels=False to prevent 
        # the colormap from 'stretching' a zero-array into a single bright color.
        self.img.setImage(self.coeff_img.T, autoLevels=False, levels=[0, 1])

        # 3. CRITICAL: Explicitly set the ViewBox state.
        # This prevents the axes from collapsing if AutoRange was active.
        vb = self.plot.getViewBox()
        vb.setRange(
            xRange=(0, self.window_len * 5), 
            yRange=(0, self.n_levels), 
            padding=0
        )
        
        # 4. Re-apply the ticks 
        # Sometimes PlotItem.clear() (if called elsewhere) wipes these
        dwt_labels = ["d3", "d4L", "d4H", "d5", "d6", "d7", "d8"]
        ticks = [(i, dwt_labels[i]) for i in range(self.n_levels)]
        self.plot.getAxis("left").setTicks([ticks])

        # 5. Force a GUI refresh
        self.plot.update()