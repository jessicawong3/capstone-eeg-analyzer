from PyQt5 import QtWidgets, QtCore, QtGui
import sys
import numpy as np
from modules.data_loader import load_eeg_data, load_hypnogram_data, get_sleep_stage_at_time, suggest_hypnogram_file
from modules.plotter import EEGPlot
from modules.mock_model import MockEEGModel
from modules.wavelet_plotter import WaveletPlot
from modules.workers import McuWorker
from modules.mcu_transfer_pipeline import DEFAULT_PORT


class Dashboard(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sleep Stage Dashboard")
        self.resize(1100, 800)



        # --- WIDGETS ---

        # mode selection using radio buttons
        self.offline_radio = QtWidgets.QRadioButton("Offline")
        self.offline_radio.setObjectName("ModeSelection")
        self.live_radio = QtWidgets.QRadioButton("Live")
        self.live_radio.setObjectName("ModeSelection")
        # set default
        self.offline_radio.setChecked(True)
        self.live_radio.setChecked(False)
        self.live_mode = False


        # load button for offline mode
        self.load_button = QtWidgets.QPushButton("Load EEG Data")
        self.load_button.setToolTip("Load EEG data from an EDF file (optionally with hypnogram)")
        

        # sleep stage options for live mode
        self.stage_container = QtWidgets.QWidget()
        # self.stage_container.setFixedHeight(40)  # match buttons' height
        stages = ["Awake", "N1", "N2", "N3", "REM"]
        self.stage_buttons = []
        stage_layout = QtWidgets.QHBoxLayout(self.stage_container)
        stage_layout.setSpacing(0)

        for stage in stages:
            btn = QtWidgets.QPushButton(stage)
            btn.setCheckable(True)
            btn.setObjectName("StageButton")
            btn.setFixedHeight(32)
            stage_layout.addWidget(btn)
            self.stage_buttons.append(btn)

        # Set default
        self.stage_buttons[0].setChecked(True)



        # EEG and wavelet plot
        self.eeg_plot = EEGPlot()
        self.wavelet_plot = WaveletPlot()


        # Start/Stop buttons
        self.start_button = QtWidgets.QPushButton("Start")
        self.stop_button = QtWidgets.QPushButton("Stop")


        # Current prediction label
        self.current_pred_value = QtWidgets.QLabel("")
        self.current_pred_value.setObjectName("BigPrediction")


        # Prediction table
        self.pred_table = QtWidgets.QTableWidget(0, 4)  # 0 rows, 4 columns
        self.pred_table.setHorizontalHeaderLabels(["Time", "Predicted", "Actual", "Confidence"])
        self.pred_table.verticalHeader().setVisible(False)
        self.pred_table.setShowGrid(True)
        self.pred_table.setAlternatingRowColors(True)
        self.pred_table.setSortingEnabled(False)  # Keep chronological order
        
        # Set up column sizing for better visibility
        header = self.pred_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed) # Time
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents) # Predicted
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents) # Actual
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch) # Confidence

        # Set fixed width for time column
        header.resizeSection(0, 70) # Time column - compact but readable

        # Set min size for table (visibility)
        self.pred_table.setMinimumWidth(320)
        self.pred_table.setMinimumHeight(200)



        # --- TOP PANEL (CONTROLS) ---

        # Top controls
        top_controls = QtWidgets.QHBoxLayout()

        # Mode selection
        top_controls.addWidget(self.offline_radio)
        top_controls.addWidget(self.live_radio)

        # Add dynamic control area to the right of the mode selection
        top_controls.addWidget(self.load_button)  # shown in offline
        top_controls.addWidget(self.stage_container)

        top_controls.addStretch()  # everything before left-aligned, after right-aligned

        top_controls.addWidget(self.start_button)
        top_controls.addWidget(self.stop_button)



        # --- LEFT PANEL (PLOTS) ---
        left_panel = QtWidgets.QVBoxLayout()
        left_panel.setSpacing(16)  # Set consistent spacing
        
        left_panel_widget = QtWidgets.QWidget()
        left_panel_widget.setLayout(left_panel)

        # Prevent excessive stretching
        left_size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        left_size_policy.setVerticalStretch(0)
        left_panel_widget.setSizePolicy(left_size_policy)

        # Cards for EEG and wavelet plots
        eeg_card = self.make_card("EEG Signal", self.eeg_plot)
        eeg_card.setMaximumHeight(400)
        wavelet_card = self.make_card("Wavelet Coefficients", self.wavelet_plot)
        wavelet_card.setMaximumHeight(400)

        left_panel.addWidget(eeg_card)
        left_panel.addWidget(wavelet_card)
        left_panel.addStretch()  # prevent cards from expanding too much



        # --- RIGHT PANEL (PREDICTIONS) ---
        right_panel = QtWidgets.QVBoxLayout()
        right_panel.setSpacing(16)  # spacing to match left panel
        
        right_panel_widget = QtWidgets.QWidget()
        right_panel_widget.setLayout(right_panel)
        right_panel_widget.setMinimumWidth(380)
        
        # ensure proper alignment
        size_policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.MinimumExpanding)
        size_policy.setVerticalStretch(0)
        right_panel_widget.setSizePolicy(size_policy)

        # Current prediction card
        pred_card = self.make_card("Current Prediction", self.current_pred_value)

        # Prediction log card
        log_card = self.make_card("Prediction Log", self.pred_table)
        log_card.setMinimumWidth(350)

        right_panel.addWidget(pred_card)
        right_panel.addWidget(log_card)
        right_panel.addStretch()



        # --- MAIN LAYOUT ---
        main_layout = QtWidgets.QVBoxLayout()
        
        # everything other than controls
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.setAlignment(QtCore.Qt.AlignTop)  # Align both panels to top
        sub_layout.setSpacing(16) 
        sub_layout.addWidget(left_panel_widget, 2)   # Use widget instead of layout
        sub_layout.addWidget(right_panel_widget, 1)  # Use widget instead of layout

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

        for btn in self.stage_buttons:
            btn.clicked.connect(self.stage_selected)



        # --- TIMER FOR FAKE ML UPDATES ---
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_prediction)
        self.model = MockEEGModel(latency=0.2)
        
        # --- DATA STORAGE ---
        self.hypno_data = None
        self.eeg_data = None
        self.eeg_times = None
        self.current_time = 0
        self.prediction_history = []

        # --- MCU ---
        self.mcu_worker = None
        self.mcu_port = DEFAULT_PORT


        # Initialize visibility based on default mode
        self.update_mode()



    # FUNCTION: loads EEG data from file
    def load_data(self):
        eeg_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open EEG EDF File", "", "EDF Files (*.edf)")
        if not eeg_path:
            return
        
        # Load the EEG data
        try:
            data, times = load_eeg_data(eeg_path)
            self.eeg_data = data
            self.eeg_times = times
            self.eeg_plot.update_plot(times, data)
            self.wavelet_plot.load_signal(data)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "EEG Loading Error", 
                f"Failed to load EEG file:\n{str(e)}")
            return

        # See if user has a hypnogram file
        reply = QtWidgets.QMessageBox.question(
            self,
            "Load Hypnogram?",
            "<html>"
            "Do you have a corresponding hypnogram file with sleep stage annotations?<br><br>"
            "Loading a hypnogram will allow you to see the actual sleep stages "
            "alongside your model's predictions for comparison."
            "</html>",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No # Default to No when no suggestions
        )  
        
        if reply == QtWidgets.QMessageBox.Yes:
            self.load_hypnogram_dialog()
    

    
    # FUNCTION: loads hypnogram data from file (called from load_data)
    def load_hypnogram_dialog(self):
        hypno_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Hypnogram EDF File", "", "EDF Files (*.edf)")
        if not hypno_path:
            return
        
        # Load hypnogram data
        try:
            onset_times, sleep_stages, durations = load_hypnogram_data(hypno_path)
            if onset_times is not None:
                self.hypno_data = (onset_times, sleep_stages, durations)
                print(f"Loaded {len(sleep_stages)} sleep stage annotations")
                
                # Display summary of loaded stages
                stage_counts = {}
                for stage in sleep_stages:
                    stage_counts[stage] = stage_counts.get(stage, 0) + 1
                print("Stage distribution:", stage_counts)
                
                # Show success message with details
                total_duration = sum(durations) / 3600  # hours
                unique_stages = len(set(sleep_stages))
                most_common_stage = max(stage_counts, key=stage_counts.get)
                
                QtWidgets.QMessageBox.information(
                    self, "Hypnogram Loaded Successfully", 
                    f"Successfully loaded sleep stage data:\n\n"
                    f"• {len(sleep_stages)} total annotations\n"
                    f"• {unique_stages} different sleep stages\n"
                    f"• Total recording duration: {total_duration:.1f} hours\n\n"
                    # f"• Most common stage: {most_common_stage}\n\n"
                    f"Ready to compare predictions vs actual stages!\n"
                )

            else:
                QtWidgets.QMessageBox.warning(
                    self, "Hypnogram Loading Error", 
                    "Failed to load hypnogram file.\n\n"
                    "Please ensure:\n"
                    "• The file is a valid EDF file\n"
                    "• The file contains sleep stage annotations\n"
                    "• The file is not corrupted\n\n"
                    "Check the console output for more details.")
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "Hypnogram Loading Error",
                f"An error occurred while loading the hypnogram:\n{str(e)}")



    # FUNCTION: starts the predictions
    def start_predictions(self):
        if self.live_radio.isChecked():
            self._start_live()
        else:
            self._start_offline()


    # FUNCTION: starts offline mode
    def _start_offline(self):
        self.current_time = 0
        self.pred_table.setRowCount(0)
        self.prediction_history.clear()
        self.timer.start(2000)  # mock model update every 2 s


    # FUNCTION: starts live mode
    def _start_live(self):
        # Open the serial port and start streaming MCU samples

        # Stop any existing worker
        self._stop_mcu_worker()

        # Get the currently selected stage
        selected_stage = self._get_selected_stage()

        # Start worker
        self.mcu_worker = McuWorker(port=self.mcu_port, stage=selected_stage)
        self.mcu_worker.chunk_ready.connect(self._on_mcu_chunk)
        self.mcu_worker.error.connect(self._on_mcu_error)
        self.eeg_plot.start_live()
        self.mcu_worker.start()


    # FUNCTION: stops the predictions
    def stop_predictions(self):
        self.timer.stop()
        self._stop_mcu_worker()
        self.eeg_plot.stop_live()


    # FUNCTION: stops an mcu worker
    def _stop_mcu_worker(self):
        if self.mcu_worker is not None:
            self.mcu_worker.stop()
            self.mcu_worker.wait()
            self.mcu_worker = None


    # SLOT: called for each chunk of preprocessed voltage samples from the MCU worker
    def _on_mcu_chunk(self, chunk):
        self.eeg_plot.append_chunk(chunk)


    # SLOT: called when the MCU worker encounters a serial error
    def _on_mcu_error(self, message: str):
        self._stop_mcu_worker()
        QtWidgets.QMessageBox.critical(self, "MCU Connection Error", message)



    # FUNCTION: updates the prediction
    def update_prediction(self):
        features = None
        stage, confs = self.model.predict(features)
        self.current_pred_value.setText(stage)

        # Get top confidence for predicted stage
        top_confidence = confs[stage]

        # Format time display
        hours = int(self.current_time // 3600)
        minutes = int((self.current_time % 3600) // 60)
        seconds = int(self.current_time % 60)
        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Get actual stage from hypnogram if available
        if self.hypno_data is not None:
            actual_stage = get_sleep_stage_at_time(self.hypno_data, self.current_time)
        else:
            actual_stage = "N/A"

        # Add new row to prediction table
        row_count = self.pred_table.rowCount()
        self.pred_table.insertRow(row_count)
        
        # Populate the new row
        self.pred_table.setItem(row_count, 0, QtWidgets.QTableWidgetItem(time_str))
        self.pred_table.setItem(row_count, 1, QtWidgets.QTableWidgetItem(stage))
        self.pred_table.setItem(row_count, 2, QtWidgets.QTableWidgetItem(actual_stage))
        self.pred_table.setItem(row_count, 3, QtWidgets.QTableWidgetItem(f"{top_confidence*100:.1f}%"))
        

        # Colour code prediction based on accuracy
        if actual_stage != "N/A" and stage == actual_stage:
            # Correct prediction
            for col in range(4):
                item = self.pred_table.item(row_count, col)
                if item:
                    item.setBackground(QtGui.QColor(200, 255, 200))  # light green

        elif actual_stage != "N/A":
            # Incorrect prediction
            for col in range(4):
                item = self.pred_table.item(row_count, col)
                if item:
                    item.setBackground(QtGui.QColor(255, 220, 220))  # light red


        # Scroll to show latest prediction
        self.pred_table.scrollToBottom()
        
        # Limit table to last 20 rows
        if row_count >= 20:
            self.pred_table.removeRow(0)

        # Increment time for next prediction (30-second epochs)
        self.current_time += 30

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
            self.stage_container.hide()
            # Stop any running MCU stream when switching to offline
            self._offline_mcu()
            self.eeg_plot.stop_live()
        else:
            self.load_button.hide()
            self.stage_container.show()
            self._start_live()



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
    

    # FUNCTION: select sleep stage (live mode)
    def stage_selected(self):
        clicked = self.sender()
        # Uncheck all others
        for btn in self.stage_buttons:
            if btn != clicked:
                btn.setChecked(False)
            else:
                btn.setChecked(True)

        selected_stage = clicked.text()
        print("Selected Stage:", selected_stage)

        # If the MCU worker is already running, restart it with the new stage
        # if self.mcu_worker is not None and self.mcu_worker.isRunning():
        self._stop_mcu_worker()
        self.mcu_worker = McuWorker(port=self.mcu_port, stage=selected_stage)
        self.mcu_worker.chunk_ready.connect(self._on_mcu_chunk)
        self.mcu_worker.error.connect(self._on_mcu_error)
        self.eeg_plot.start_live()
        print("Restarting? should be with stage ", selected_stage)
        self.mcu_worker.start()


    # FUNCTION: gets the selected stage
    def _get_selected_stage(self):
        # Return text of whichever stage button is currently checked
        for btn in self.stage_buttons:
            if btn.isChecked():
                print("get_selected_stage: ", btn.text())
                return btn.text()
        # return "Awake"  # fallback


    # FUNCTION: turn mcu offline
    def _offline_mcu(self):
        self._stop_mcu_worker()
        self.mcu_worker = McuWorker(port=self.mcu_port, stage="Offline")
        self.mcu_worker.error.connect(self._on_mcu_error)
        print("Restarting? should be with stage ", "Offline")
        self.mcu_worker.start()
        self._stop_mcu_worker()




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
