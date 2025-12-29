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
        self.resize(1000, 800)



        # --- WIDGETS ---

        # mode selection using radio buttons
        self.offline_radio = QtWidgets.QRadioButton("Offline")
        self.offline_radio.setObjectName("ModeSelection")
        self.live_radio = QtWidgets.QRadioButton("Live")
        self.live_radio.setObjectName("ModeSelection")
        # set default
        self.offline_radio.setChecked(True)
        self.live_mode = False


        # load button for offline mode
        self.load_button = QtWidgets.QPushButton("Load EEG Data")
        self.load_button.setToolTip("Load EEG data from an EDF file")
        

        # sleep stage options for live mode
        self.stage_label = QtWidgets.QLabel("Select Sleep Stage:")
        self.stage_combo = QtWidgets.QComboBox()
        self.stage_combo.addItems(["Awake", "N1", "N2", "N3", "REM"])


        # EEG and wavelet plot
        self.eeg_plot = EEGPlot()
        self.wavelet_plot = WaveletPlot()


        # Start/Stop buttons
        self.start_button = QtWidgets.QPushButton("Start")
        self.stop_button = QtWidgets.QPushButton("Stop")


        # Current prediction label
        self.current_pred_value = QtWidgets.QLabel("Awake")
        self.current_pred_value.setObjectName("BigPrediction")


        # Prediction table
        self.pred_table = QtWidgets.QTableWidget(5, 3)
        self.pred_table.setHorizontalHeaderLabels(["Time", "Stage", "Confidence"])
        self.pred_table.verticalHeader().setVisible(False)
        self.pred_table.setShowGrid(False)
        self.pred_table.horizontalHeader().setStretchLastSection(True)
        self.pred_table.setAlternatingRowColors(True)



        # --- TOP PANEL (CONTROLS) ---

        # Top controls
        top_controls = QtWidgets.QHBoxLayout()

        # Mode selection
        top_controls.addWidget(self.offline_radio)
        top_controls.addWidget(self.live_radio)

        # Add dynamic control area to the right of the mode selection
        top_controls.addWidget(self.load_button)  # shown in offline
        top_controls.addWidget(self.stage_label)
        top_controls.addWidget(self.stage_combo)

        top_controls.addStretch()  # everything before left-aligned, after right-aligned

        top_controls.addWidget(self.start_button)
        top_controls.addWidget(self.stop_button)



        # --- LEFT PANEL (PLOTS) ---
        left_panel = QtWidgets.QVBoxLayout()

        # Cards for EEG and wavelet plots
        eeg_card = self.make_card("EEG Signal", self.eeg_plot)
        wavelet_card = self.make_card("Wavelet Coefficients", self.wavelet_plot)

        left_panel.addWidget(eeg_card)
        left_panel.addWidget(wavelet_card)



        # --- RIGHT PANEL (PREDICTIONS) ---
        right_panel = QtWidgets.QVBoxLayout()

        # Current prediction card
        pred_card = self.make_card("Current Prediction", self.current_pred_value)

        # Prediction log card
        log_card = self.make_card("Prediction Log", self.pred_table)

        # right_panel.setSpacing(16)

        right_panel.addWidget(pred_card)
        right_panel.addWidget(log_card)
        right_panel.addStretch()



        # --- MAIN LAYOUT ---
        main_layout = QtWidgets.QVBoxLayout()
        
        # everything other than controls
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.addLayout(left_panel, 3)
        sub_layout.addLayout(right_panel, 1)

        # sub_layout.setContentsMargins(16, 16, 16, 16)
        # sub_layout.setSpacing(16)

        # add controls and sublayout to main layout
        main_layout.addLayout(top_controls)
        main_layout.addLayout(sub_layout)

        self.setLayout(main_layout)



        # --- SIGNALS ---
        self.load_button.clicked.connect(self.load_data)
        self.start_button.clicked.connect(self.start_predictions)
        self.stop_button.clicked.connect(self.stop_predictions)
        self.offline_radio.toggled.connect(self.update_mode)
        self.live_radio.toggled.connect(self.update_mode)



        # --- TIMER FOR FAKE ML UPDATES ---
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_prediction)
        self.model = MockEEGModel(latency=0.2)


        # Initialize visibility based on default mode
        self.update_mode()



    # FUNCTION: loads EEG data from file
    def load_data(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open EEG EDF", "", "EDF Files (*.edf)")
        if path:
            data, times = load_eeg_data(path)
            self.eeg_plot.update_plot(times, data)
            self.wavelet_plot.load_signal(data)



    # FUNCTION: starts the predictions
    def start_predictions(self):
        self.timer.start(2000)  # every 2 seconds



    # FUNCTION: stops the predictions
    def stop_predictions(self):
        self.timer.stop()



    # FUNCTION: updates the prediction
    def update_prediction(self):
        features = None  # Placeholder for real features
        stage, confs = self.model.predict(features)
        self.current_pred_value.setText(stage)
        for i, (s, c) in enumerate(confs.items()):
            self.pred_table.setItem(i, 0, QtWidgets.QTableWidgetItem(s))
            self.pred_table.setItem(i, 1, QtWidgets.QTableWidgetItem(f"{c*100:.1f}%"))

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



    # FUNCTION: updates layout based on mode (offline/live)
    def update_mode(self):
        if self.offline_radio.isChecked():
            self.load_button.show()
            self.stage_label.hide()
            self.stage_combo.hide()
        else:
            self.load_button.hide()
            self.stage_label.show()
            self.stage_combo.show()



    # FUNCTION: create a card widget for layout
    def make_card(self, title: str, content: QtWidgets.QWidget):
        card = QtWidgets.QFrame()
        card.setObjectName("Card")

        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        label = QtWidgets.QLabel(title)
        label.setObjectName("CardTitle")

        layout.addWidget(label)
        layout.addWidget(content)

        return card



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    # read and set stylesheet file
    try:
        with open("./styles.qss", "r") as f:
            _style = f.read()
        app.setStyleSheet(_style)
    except FileNotFoundError:
        print("Stylesheet file not found, running without style.")

    win = Dashboard()
    win.show()
    sys.exit(app.exec_())
