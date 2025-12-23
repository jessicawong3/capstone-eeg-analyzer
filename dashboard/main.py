from PyQt5 import QtWidgets, QtCore
import sys
import numpy as np
from modules.data_loader import load_eeg_data
from modules.plotter import EEGPlot
from modules.mock_model import MockEEGModel
from modules.wavelet_plotter import WaveletPlot



class Dashboard(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sleep Stage Dashboard")
        self.resize(1000, 600)

        # === Widgets ===
        self.load_btn = QtWidgets.QPushButton("Load EEG Data")
        self.load_btn.setToolTip("Load EEG data from an EDF file")
        
        # Mode selection using radio buttons
        self.offline_radio = QtWidgets.QRadioButton("Offline")
        self.live_radio = QtWidgets.QRadioButton("Live")
        self.offline_radio.setChecked(True)  # default
        self.live_mode = False

        # Sleep stage options (only for live mode)
        self.stage_label = QtWidgets.QLabel("Select Sleep Stage:")
        self.stage_combo = QtWidgets.QComboBox()
        self.stage_combo.addItems(["Awake", "N1", "N2", "N3", "REM"])

        # EEG plot
        self.eeg_plot = EEGPlot()
        self.wavelet_plot = WaveletPlot()

        # Predictions panel
        self.start_btn = QtWidgets.QPushButton("Start Predictions")
        # self.stop_btn = QtWidgets.QPushButton("Stop")
        self.pred_label = QtWidgets.QLabel("Predicted Stage: None")
        self.conf_table = QtWidgets.QTableWidget(5, 2)
        self.conf_table.setHorizontalHeaderLabels(["Stage", "Confidence"])
        self.conf_table.verticalHeader().setVisible(False)

        # === Left panel (Controls + Plot) ===
        left_panel = QtWidgets.QVBoxLayout()

        # Top controls
        top_controls = QtWidgets.QHBoxLayout()

        # Mode selection
        top_controls.addWidget(self.offline_radio)
        top_controls.addWidget(self.live_radio)

        # Add dynamic control area to the right of the mode selection
        top_controls.addWidget(self.load_btn)  # shown in offline
        top_controls.addWidget(self.stage_label)
        top_controls.addWidget(self.stage_combo)
        
        top_controls.addStretch()  # Push everything left for neatness
        left_panel.addLayout(top_controls)
        left_panel.addWidget(self.eeg_plot)
        left_panel.addWidget(self.wavelet_plot)

        # === Right panel (Predictions) ===
        right_panel = QtWidgets.QVBoxLayout()
        right_panel.addWidget(self.start_btn)
        # right_panel.addWidget(self.stop_btn)
        right_panel.addWidget(self.pred_label)
        right_panel.addWidget(self.conf_table)
        right_panel.addStretch()

        # === Main layout ===
        main_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(left_panel, 3)
        main_layout.addLayout(right_panel, 1)

        self.setLayout(main_layout)

        # === Signals ===
        self.load_btn.clicked.connect(self.load_data)
        self.start_btn.clicked.connect(self.start_predictions)
        # self.stop_btn.clicked.connect(self.stop_predictions)
        self.offline_radio.toggled.connect(self.update_mode)
        self.live_radio.toggled.connect(self.update_mode)

        # === Timer for fake ML updates ===
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_prediction)
        self.model = MockEEGModel(latency=0.2)

        # Initialize visibility based on default mode
        self.update_mode()

    def load_data(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open EEG EDF", "", "EDF Files (*.edf)")
        if path:
            data, times = load_eeg_data(path)
            self.eeg_plot.update_plot(times, data)

    def start_predictions(self):
        self.timer.start(2000)  # every 2 seconds

    # def stop_predictions(self):
    #     self.timer.stop()

    def update_prediction(self):
        features = None  # Placeholder for real features
        stage, confs = self.model.predict(features)
        self.pred_label.setText(f"Predicted Stage: {stage}")
        for i, (s, c) in enumerate(confs.items()):
            self.conf_table.setItem(i, 0, QtWidgets.QTableWidgetItem(s))
            self.conf_table.setItem(i, 1, QtWidgets.QTableWidgetItem(f"{c*100:.1f}%"))

        # --- SAMPLE COEFF STREAM ---
        coeffs = {
            "A5": np.random.random(),
            "D5": np.random.random(),
            "D4": np.random.random(),
            "D3": np.random.random(),
            "D2": np.random.random(),
            "D1": np.random.random()
        }

        # Update the live wavelet visualization
        self.wavelet_plot.update_coeffs(coeffs)

    def update_mode(self):
        if self.offline_radio.isChecked():
            self.load_btn.show()
            self.stage_label.hide()
            self.stage_combo.hide()
        else:
            self.load_btn.hide()
            self.stage_label.show()
            self.stage_combo.show()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = Dashboard()
    win.show()
    sys.exit(app.exec_())
