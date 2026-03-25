from PyQt5 import QtWidgets, QtCore, QtGui
import sys
import numpy as np
from collections import deque
from modules.data_loader import load_eeg_data, load_npy_eeg_data, load_hypnogram_data, load_npy_hypnogram_data, get_sleep_stage_at_time, extract_npy_from_npz
from modules.plotter import EEGPlot
from modules.mock_model import MockEEGModel
from modules.wavelet_plotter import WaveletPlot
from modules.workers import McuWorker, FPGAReceiverWorker, FPGAStartWorker, FPGAStopWorker
from modules.mcu_transfer_pipeline import DEFAULT_PORT
from modules.preprocess import get_graph_data_from_data, get_pred_data_from_data
from modules.pynq_transfer_pipeline import setup_ssh_connection, signal_fpga_process_file
from uploader import UploadProgressDialog

class Dashboard(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sleep Stage Dashboard")
        self.resize(1050, 800)


        # --- WIDGETS ---

        # mode selection using radio buttons
        self.real_data_radio = QtWidgets.QRadioButton("Real Data")
        self.real_data_radio.setObjectName("ModeSelection")
        self.synthetic_radio = QtWidgets.QRadioButton("Synthetic")
        self.synthetic_radio.setObjectName("ModeSelection")
        # set default
        self.real_data_radio.setChecked(True)
        self.synthetic_radio.setChecked(False)
        self.synthetic_mode = False


        # load button for real data mode
        self.load_button = QtWidgets.QPushButton("Load EEG Data")
        self.load_button.setToolTip("Load EEG data from an EDF file (optionally with hypnogram)")
        

        # sleep stage options for synthetic mode
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
        top_controls.addWidget(self.real_data_radio)
        top_controls.addWidget(self.synthetic_radio)

        # Add dynamic control area to the right of the mode selection
        top_controls.addWidget(self.load_button)  # shown in real data
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

        # Card for signal label (file name for real data mode, sleep stage for synthetic mode)
        self.signal_label = QtWidgets.QLabel("")
        self.signal_label.setObjectName("SignalLabel")
        self.signal_card = self.make_signal_card("Signal:", self.signal_label)

        # Cards for EEG and wavelet plots
        eeg_card = self.make_card("EEG Signal", self.eeg_plot)
        eeg_card.setMaximumHeight(400)
        wavelet_card = self.make_card("Wavelet Coefficients", self.wavelet_plot)
        wavelet_card.setMaximumHeight(400)

        left_panel.addWidget(self.signal_card)
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
        right_panel.addWidget(log_card, 1)  # Add stretch factor to make it expand vertically



        # --- MAIN LAYOUT ---
        main_layout = QtWidgets.QVBoxLayout()
        
        # everything other than controls
        sub_layout = QtWidgets.QHBoxLayout()
        sub_layout.setAlignment(QtCore.Qt.AlignTop)  # Align both panels to top
        sub_layout.setSpacing(8)  # Reduced spacing to match single padding width
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
        self.real_data_radio.toggled.connect(self.update_mode)
        self.synthetic_radio.toggled.connect(self.update_mode)

        for btn in self.stage_buttons:
            btn.clicked.connect(self.stage_selected)



        # --- TIMER FOR FAKE ML UPDATES ---
        # self.timer = QtCore.QTimer()
        # self.timer.timeout.connect(self.update_prediction)
        # self.model = MockEEGModel(latency=0.2)
        
        # --- TIMER FOR WAVELET PLOT UPDATES FROM FPGA QUEUE ---
        self.wavelet_update_timer = QtCore.QTimer()
        self.wavelet_update_timer.timeout.connect(self._process_wavelet_queue)
        self.wavelet_update_timer.setInterval(5000)  # Update every 5000ms to match ~0.2 Hz display rate

        # --- TIMER FOR FPGA PREDICTIONS ---
        self.prediction_timer = QtCore.QTimer()
        self.prediction_timer.timeout.connect(self._process_prediction_queue)
        self.prediction_timer.setInterval(5000)  # Update predictions every 5 seconds to match epoch duration

        # --- DATA STORAGE ---
        self.hypno_data = None
        self.eeg_data = None
        self.eeg_times = None
        self.current_time = 0
        self.prediction_history = []
        self.loaded_eeg_filename = None  # Track the loaded file name for display
        # --- MCU ---
        self.mcu_worker = None
        self.mcu_port = DEFAULT_PORT

        # --- FPGA START WORKER ---
        self.fpga_start_worker = None

        # --- FPGA STOP WORKER ---
        self.fpga_stop_worker = None

        # --- FPGA TCP RECEIVER ---
        self.fpga_receiver = None
        self.fpga_playback_active = False  # Flag to control when wavelet updates
        self.fpga_coefficient_queue = deque()  # Queue to store multiple sets of coefficients (FIFO)
        self.fpga_prediction_queue = deque()  # Queue to store multiple predictions (FIFO)
        self.prediction_second_counter = 0  # Counter to track seconds for 5-second prediction intervals
        self._start_fpga_receiver()

        # --- SSH CONNECTION TO PYNQ ---
        # Set up SSH connection to PYNQ board at startup
        self.pynq_host = "192.168.137.28"  # PYNQ IP 192.168.137.28  127.0.0.1. #CHANGE
        self.ssh_connection = None
        self._setup_ssh_connection()


        # Initialize visibility based on default mode
        self.update_mode()



    # FUNCTION: loads EEG data from file
    def load_data(self):
        # get either an eeg file or an npz (for demo purposes)
        eeg_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open EEG EDF File", "", "EDF Files (*.edf || *.npz || *.npy)")
        if not eeg_path:
            return
        
        # Load the EEG data
        try:
            if eeg_path.endswith(".npz"):
                extract_npy_from_npz(eeg_path, "test_data")
            elif eeg_path.endswith(".npy"):
                data, times = load_npy_eeg_data(eeg_path)
                print(f"Loaded EEG data with shape {data.shape} and times shape {times.shape}")
                self.eeg_data = data
                self.eeg_times = times
            else:
                data, times = load_eeg_data(eeg_path)
                self.eeg_data = data
                self.eeg_times = times
            self.eeg_plot.update_plot(times, data)
            # self.wavelet_plot.load_signal(data)
            self._real_data_rolling_active = False  # Reset flag for new data
            
            # Store and display the filename in the signal card
            self.loaded_eeg_filename = eeg_path.split('/')[-1]  # Extract just the filename
            self._update_signal_card()
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, "EEG Loading Error", 
                f"Failed to load EEG file:\n{str(e)}")
            return

        # Upload file to the PYNQ board
        mode = "synthetic" if self.synthetic_radio.isChecked() else "real_data"
        dialog = UploadProgressDialog(eeg_path, fpga_receiver=self.fpga_receiver, mode=mode, parent=self)
        result = dialog.exec_()   # blocks UI interaction but NOT the event loop
        if result == QtWidgets.QDialog.Rejected:
            QtWidgets.QMessageBox.warning(
                self, "Upload Failed",
                f"The file could not be transferred to the PYNQ board:\n\n{dialog.error_message()}\n\n"
                "You can still use the file locally for offline analysis."
            )

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
            self, "Open Hypnogram EDF File", "", "EDF Files (*.edf || *.npz || *.npy)")
        if not hypno_path:
            return
        
        # Load hypnogram data
        try:
            if hypno_path.endswith(".npy"):
                onset_times, sleep_stages, durations = load_npy_hypnogram_data(hypno_path)
            else:
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
        # Start EEG plot
        if self.synthetic_radio.isChecked():
            self._start_synthetic()
            # Signal FPGA to start processing in synthetic mode
            self._signal_fpga_synthetic_mode()
        else:
            self._start_real_data()

        # Enable FPGA playback before starting
        self.fpga_playback_active = True
        print("FPGA playback enabled")
        
        # Start wavelet update timer to consume queue at steady rate
        self.wavelet_update_timer.start()
        
        # Start prediction update timer to consume prediction queue
        self.prediction_timer.start()
        
        # Start wavelet plot - display any buffered FPGA data
        if self.fpga_coefficient_queue:
            coefficients = self.fpga_coefficient_queue.popleft()
            print(f"Using buffered FPGA coefficients from queue. Queue size: {len(self.fpga_coefficient_queue)}")
            self.wavelet_plot.update_from_fpga(coefficients)
        else:
            print("No buffered FPGA data available. Wavelet plot will remain empty until data arrives.")

        # Start predictions - display any buffered prediction data
        if self.fpga_prediction_queue:
            # pred_data = self.prediction_queue.popleft()
            print(f"Using buffered prediction data from queue. Queue size: {len(self.fpga_prediction_queue)}")
            self._process_prediction_queue()
        else:
            print("No buffered prediction data available. Log will remain empty until data arrives.")



    # FUNCTION: starts real data mode
    def _start_real_data(self):
        # Check if data has been loaded
        if self.eeg_data is None or self.eeg_times is None:
            QtWidgets.QMessageBox.warning(
                self, "No Data Loaded",
                "Please load EEG data first before starting playback."
            )
            return

        # Start rolling playback of real data
        # Determine sampling frequency from the data
        if len(self.eeg_times) > 1:
            fs = 1.0 / (self.eeg_times[1] - self.eeg_times[0])
        else:
            fs = 256  # fallback
        
        # Check if we're resuming (plot is already in rolling mode) or starting fresh
        resume = getattr(self, '_real_data_rolling_active', False)
        self.eeg_plot.start_real_data_rolling(self.eeg_times, self.eeg_data, int(fs), resume=resume)
        self._real_data_rolling_active = True
        
        # Start timer to advance through data (same rate as synthetic mode)
        # Each timer tick advances by CHUNK_SIZE samples at the given fs
        from modules.plotter import LIVE_WINDOW
        chunk_size = 32  # Same as CHUNK_SIZE in workers
        interval_ms = int((chunk_size / fs) * 1000)
        self.real_data_timer = QtCore.QTimer()
        self.real_data_timer.timeout.connect(self.advance_real_data_plot)
        self.real_data_timer.start(interval_ms)


    # FUNCTION: starts synthetic mode
    def _start_synthetic(self):

        # Stop any existing worker and wait briefly for cleanup
        # Use a very short timeout (100ms) - just to ensure it exits quickly
        if self.mcu_worker is not None:
            self.mcu_worker.stop()
            # Give it a very short time to finish (100ms should be enough with port closed)
            self.mcu_worker.wait(100)
            # Now we can safely create a new worker

        # Get the currently selected stage
        selected_stage = self._get_selected_stage()

        # Start worker
        self.mcu_worker = McuWorker(port=self.mcu_port, stage=selected_stage)
        self.mcu_worker.chunk_ready.connect(self._on_mcu_chunk)
        self.mcu_worker.error.connect(self._on_mcu_error)
        self.eeg_plot.start_synthetic(stage=selected_stage)
        self.mcu_worker.start()

    # FUNCTION: stops the predictions
    def stop_predictions(self):
        # Disable FPGA playback
        self.fpga_playback_active = False
        print("FPGA playback disabled")
        
        # Stop wavelet update timer
        self.wavelet_update_timer.stop()
        
        # Stop prediction timer
        self.prediction_timer.stop()
        
        # self.timer.stop() 
        self._stop_mcu_worker()
        self._stop_fpga_start_worker()
        # Also stop real data timer if it exists
        if hasattr(self, 'real_data_timer'):
            self.real_data_timer.stop()
        self.eeg_plot.stop_synthetic()


    # FUNCTION: stops an mcu worker
    def _stop_mcu_worker(self):
        """Stop MCU worker without blocking the UI thread."""
        if self.mcu_worker is not None:
            # Signal the worker to stop (this closes the serial port immediately)
            # Do NOT wait on UI thread - that blocks the entire event loop and freezes the UI
            self.mcu_worker.stop()
            # The worker will finish in the background
            # NOTE: We intentionally do NOT call wait() here as it blocks the UI thread

    # FUNCTION: stops the FPGA start worker
    def _stop_fpga_start_worker(self):
        if self.fpga_start_worker is not None:
            self.fpga_start_worker.quit()
            # Do NOT wait on UI thread - that blocks the event loop
            # The worker will finish in the background

    # FUNCTION: stops the FPGA in background to avoid UI blocking
    def _stop_fpga_background(self, mode: str = "real_data"):
        """Stop FPGA processing in background thread to prevent UI stalls."""
        # Clean up any existing stop worker (non-blocking with timeout)
        if self.fpga_stop_worker is not None:
            if self.fpga_stop_worker.isRunning():
                self.fpga_stop_worker.stopped.disconnect()  # Disconnect old signals
                self.fpga_stop_worker.error.disconnect()
        
        # Start new stop worker
        self.fpga_stop_worker = FPGAStopWorker(mode=mode)
        self.fpga_stop_worker.stopped.connect(self._on_fpga_stop_complete)
        self.fpga_stop_worker.error.connect(self._on_fpga_stop_error)
        self.fpga_stop_worker.start()

    # SLOT: called when FPGA stop worker completes
    def _on_fpga_stop_complete(self):
        print("FPGA stop completed")
    
    # SLOT: called when FPGA stop worker encounters an error
    def _on_fpga_stop_error(self, message: str):
        print(f"FPGA stop error: {message}")

    # SLOT: called for each chunk of preprocessed voltage samples from the MCU worker
    def _on_mcu_chunk(self, chunk):
        self.eeg_plot.append_chunk(chunk)

    # SLOT: called each timer tick to advance real data playback
    def advance_real_data_plot(self):
        """Advance the rolling plot with the next chunk of real data."""
        chunk_size = 32  # Same as CHUNK_SIZE in workers
        more_data = self.eeg_plot.append_real_data_chunk(chunk_size)
        
        if not more_data:
            # Reached end of data
            self.stop_predictions()

    # SLOT: called when the MCU worker encounters a serial error
    def _on_mcu_error(self, message: str):
        self._stop_mcu_worker()
        QtWidgets.QMessageBox.critical(self, "MCU Connection Error", message)


    # FUNCTION: updates layout based on mode (real data / synthetic)
    def update_mode(self):
        """Handle mode switching with complete cleanup of state."""
        print("Switching modes - initiating cleanup...")
        
        # Determine which mode WAS running before switching
        # (check actual running state, not radio button state which has already changed)
        mcu_was_running = self.mcu_worker is not None and self.mcu_worker.isRunning()
        previous_mode = "synthetic" if mcu_was_running else "real_data"
        
        # Stop any running playback/predictions
        self.stop_predictions()

        # Stop FPGA processing in background to avoid UI blocking
        self._stop_fpga_background(mode=previous_mode)
        
        # Reset the FPGA receiver flag for next mode
        if self.fpga_receiver:
            self.fpga_receiver.reset_first_data_flag()
        
        # Clear FPGA data queues (important - prevents stale data from appearing in new mode)
        print("Clearing FPGA data queues...")
        self.fpga_coefficient_queue.clear()
        self.fpga_prediction_queue.clear()
        self.prediction_second_counter = 0
        
        # Clear the prediction table and history
        print("Clearing prediction table and history...")
        self.pred_table.setRowCount(0)
        self.prediction_history.clear()
        self.current_pred_value.setText("")
        self.current_time = 0
        self.hypno_data = None
        
        # Reset the real data rolling flag
        self._real_data_rolling_active = False
        
        # Reset FPGA playback flag
        self.fpga_playback_active = False
        
        # Clear EEG plot (resets drawing and graph state)
        print("Clearing EEG plot...")
        self.eeg_plot.clear()
        self.eeg_data = None
        self.eeg_times = None
        self.loaded_eeg_filename = None
        
        # Clear wavelet plot
        print("Clearing wavelet plot...")
        self.wavelet_plot.reset_plot()
        

        print("Cleaning up mode-specific resources...")
        if self.real_data_radio.isChecked():
            self.load_button.show()
            self.stage_container.hide()
            # Stop any running MCU stream when switching to real data
            self._offline_mcu()
            self.eeg_plot.stop_synthetic()
        else:
            self.load_button.hide()
            self.stage_container.show()
            # Synthetic mode doesn't use MCU, but ensure it's stopped
            self._stop_mcu_worker()
            # # Signal FPGA to start processing in synthetic mode
            # self._signal_fpga_synthetic_mode()
        
        # Update signal card based on new mode
        self._update_signal_card()
        print("Mode switch complete")



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
    

    # FUNCTION: create a signal card widget with title and content on same line
    def make_signal_card(self, title: str, content: QtWidgets.QWidget):
        card = QtWidgets.QFrame()
        card.setObjectName("Card")

        layout = QtWidgets.QHBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        label = QtWidgets.QLabel(title)
        label.setObjectName("CardTitle")

        layout.addWidget(label)
        layout.addWidget(content)
        layout.addStretch()  # Push content to the left

        return card
    

    # FUNCTION: select sleep stage (synthetic mode)
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
        
        # Clear queues when sleep stage changes to avoid mixing data from old stage
        print("Clearing FPGA data queues due to stage change...")
        self.fpga_coefficient_queue.clear()
        self.fpga_prediction_queue.clear()
        self.prediction_second_counter = 0

        # If the MCU worker is already running, just swap the stage without restarting
        if self.mcu_worker is not None and self.mcu_worker.isRunning():
            # Just update the stage in the worker without stopping/restarting
            self.mcu_worker.set_stage(selected_stage)
            # Update the plot's current stage so it knows we're still in the same session
            self.eeg_plot._current_stage = selected_stage 
        
        # Update signal card to display the new selected stage
        self._update_signal_card() 


    # FUNCTION: gets the selected stage
    def _get_selected_stage(self):
        for btn in self.stage_buttons:
            if btn.isChecked():
                print("get_selected_stage: ", btn.text())
                return btn.text()
        return "Offline"  # fallback


    # FUNCTION: update signal card content based on current mode
    def _update_signal_card(self):
        """Update the signal card to display file name (real data) or sleep stage (synthetic)"""
        if self.real_data_radio.isChecked():
            # Real data mode: display filename or "awaiting file"
            if self.loaded_eeg_filename:
                self.signal_label.setText(self.loaded_eeg_filename)
            else:
                self.signal_label.setText("Awaiting file")
        else:
            # Synthetic mode: display currently selected sleep stage
            selected_stage = self._get_selected_stage()
            self.signal_label.setText(selected_stage)


    # FUNCTION: set up SSH connection to PYNQ board
    def _setup_ssh_connection(self):
        """Set up persistent SSH connection to PYNQ board at dashboard startup"""
        try:
            self.ssh_connection = setup_ssh_connection(
                host=self.pynq_host,
                username="xilinx" #"xilinx" None # Default: current system user (change to xilinx) # CHANGE
            )
            print(f"SSH connection to PYNQ ({self.pynq_host}) established successfully")
        except Exception as e:
            print(f"Warning: Could not establish SSH connection to PYNQ at startup: {e}")
            print("File uploads will fail until SSH is configured. Update self.pynq_host and try again.")
            self.ssh_connection = None


    def _signal_fpga_synthetic_mode(self):
        """Signal the FPGA to start processing in synthetic mode (non-blocking)"""
        # Stop any existing FPGA start worker
        if self.fpga_start_worker is not None:
            self.fpga_start_worker.quit()
            self.fpga_start_worker.wait()
        
        # Create and start FPGA start worker to avoid blocking the UI
        filename = "synthetic_data.npz"
        self.fpga_start_worker = FPGAStartWorker(filename=filename, mode="synthetic")
        self.fpga_start_worker.started.connect(lambda: print("FPGA synthetic mode started successfully"))
        self.fpga_start_worker.error.connect(self._on_fpga_start_error)
        # Clean up when worker is finished
        self.fpga_start_worker.finished.connect(self._on_fpga_start_worker_finished)
        self.fpga_start_worker.start()

    def _on_fpga_start_worker_finished(self):
        """Clean up FPGA start worker after it finishes"""
        if self.fpga_start_worker is not None:
            self.fpga_start_worker.deleteLater()
            self.fpga_start_worker = None

    def _on_fpga_start_error(self, message: str):
        """Handle errors from FPGA start worker"""
        print(f"FPGA Start Error: {message}")
        # Optionally show user a warning, but don't crash the entire pipeline


    # FUNCTION: start FPGA TCP receiver
    def _start_fpga_receiver(self):
        """Start the FPGA receiver to listen for incoming data on TCP port"""
        # Get the user's current IP address
        local_ip = self._get_local_ip()

        self.fpga_receiver = FPGAReceiverWorker(host="192.168.137.1", port=9999) # CHANGE
        # self.fpga_receiver = FPGAReceiverWorker(host=local_ip, port=9999)
        self.fpga_receiver.data_ready.connect(self._on_fpga_data_received)
        self.fpga_receiver.error.connect(self._on_fpga_error)
        self.fpga_receiver.start()
        print(f"FPGA Receiver started and listening on 192.168.137.1:9999...") # CHANGE
        # print(f"FPGA Receiver started and listening on {local_ip}:9999...")


    # FUNCTION: get the user's local IP address
    def _get_local_ip(self):
        """Get the machine's local IP address (non-loopback)"""
        import socket
        try:
            # Connect to a remote server (doesn't need to actually connect)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            print(f"Detected local IP address: {ip}")
            return ip
        except Exception as e:
            print(f"Could not detect local IP ({e}), falling back to 0.0.0.0")
            return "0.0.0.0"  # fallback to all interfaces


    # SLOT: called when FPGA sends data over TCP
    def _on_fpga_data_received(self, eeg_array, result_array):
        """Process received EEG data from FPGA"""
        print(f"Dashboard received EEG {eeg_array.shape} and result {result_array.shape}")
        
        # Extract 1 data point from every 5-second window from the full 30-second buffer
        # eeg_array shape: (7, 960) - full 30-second epochs
        # get_graph_data_from_data returns: (7, 6) - 6 timepoints per epoch
        fpga_coefficients = get_graph_data_from_data(eeg_array)
        print(f"FPGA coefficients shape: {fpga_coefficients.shape}")

        # Add coefficients to queue (FIFO)
        # for each timepoint in the 5-second window
        for i in range(fpga_coefficients.shape[1]):
            self.fpga_coefficient_queue.append(fpga_coefficients[:, i])

        print(f"FPGA coefficients added to queue. Queue size: {len(self.fpga_coefficient_queue)}. Playback active: {self.fpga_playback_active}")

        
        # Only extract prediction every 5 seconds
        if self.prediction_second_counter % 5 == 0:
            # Extract the prediction data for this second
            # result_array[:, second_idx] gives us [pred_index, conf_awake, conf_n1, conf_n2, conf_n3, conf_rem]
            # flatten data first
            flattened_pred = result_array.flatten()
            pred_data = get_pred_data_from_data(flattened_pred)
            print(f"FPGA prediction at second {self.prediction_second_counter}: {pred_data}")
            
            # Add prediction to queue (FIFO)
            self.fpga_prediction_queue.append(pred_data)
            print(f"FPGA prediction added to queue. Queue size: {len(self.fpga_prediction_queue)}")
        else:
            print(f"Dropping prediction at second {self.prediction_second_counter} (not a 5-second interval)")

        self.prediction_second_counter += 1


    # FUNCTION: clear the wavelet plot (shows empty / no colors)
    def _clear_wavelet_plot(self):
        """Clear the wavelet plot by setting all coefficients to zero"""
        empty_coefficients = np.zeros(6)
        self.wavelet_plot.update_from_fpga(empty_coefficients)


    # SLOT: called by timer to process wavelet queue at steady rate
    def _process_wavelet_queue(self):
        """Process the FPGA coefficient queue at a steady rate without blocking other processes"""
        if not self.fpga_playback_active:
            return
        
        # If we have data in queue, consume the oldest entry
        if self.fpga_coefficient_queue:
            coefficients_to_display = self.fpga_coefficient_queue.popleft()
            print(f"Displaying queued coefficients. Remaining in queue: {len(self.fpga_coefficient_queue)}")
            self.wavelet_plot.update_from_fpga(coefficients_to_display)
        else:
            # Queue is empty, clear the wavelet plot (no colors)
            # Only log this occasionally to avoid spam
            if not hasattr(self, '_queue_empty_logged'):
                self._queue_empty_logged = True
                print("No coefficients in queue. Wavelet plot idle.")


    # SLOT: called by timer to process prediction queue every 5 seconds
    def _process_prediction_queue(self):
        """Process FPGA predictions from queue and display them"""
        print(f"_process_prediction_queue called. Playback active: {self.fpga_playback_active}, Queue size: {len(self.fpga_prediction_queue)}")
        if not self.fpga_playback_active:
            print("Playback not active, returning")
            return
        
        # If we have a prediction in queue, consume it and display
        if self.fpga_prediction_queue:
            pred_data = self.fpga_prediction_queue.popleft()
            # pred_data = [prediction_index (0-4), confidence_value]
            prediction_index = int(pred_data[0])
            confidence = float(pred_data[1])
            
            # Map prediction index to stage name
            stage_names = ["Awake", "N1", "N2", "N3", "REM"]
            stage = stage_names[prediction_index] if 0 <= prediction_index < len(stage_names) else "Unknown"
            
            print(f"Displaying FPGA prediction: {stage} (confidence: {confidence:.4f}). Remaining in queue: {len(self.fpga_prediction_queue)}")
            
            # Update the current prediction display
            self.current_pred_value.setText(stage)
            
            # Format time display
            hours = int(self.current_time // 3600)
            minutes = int((self.current_time % 3600) // 60)
            seconds = int(self.current_time % 60)
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # In synthetic mode use the selected stage as the "actual" stage
            if not self.real_data_radio.isChecked():
                actual_stage = self._get_selected_stage()
            # Get actual stage from hypnogram if available (real data mode)
            elif self.hypno_data is not None:
                actual_stage = get_sleep_stage_at_time(self.hypno_data, self.current_time)
            else:
                actual_stage = "N/A"
            
            # Add new row to prediction table
            row_count = self.pred_table.rowCount()
            print(f"Adding row to pred_table. Current row count: {row_count}")
            self.pred_table.insertRow(row_count)
            print(f"Row inserted. New row count: {self.pred_table.rowCount()}")
            
            # Populate the new row
            self.pred_table.setItem(row_count, 0, QtWidgets.QTableWidgetItem(time_str))
            self.pred_table.setItem(row_count, 1, QtWidgets.QTableWidgetItem(stage))
            self.pred_table.setItem(row_count, 2, QtWidgets.QTableWidgetItem(actual_stage))
            self.pred_table.setItem(row_count, 3, QtWidgets.QTableWidgetItem(f"{confidence*100:.1f}%"))
            
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
            # if row_count >= 20:
            #     self.pred_table.removeRow(0)
            
            # Increment time for next prediction
            self.current_time += 5
        else:
            print("No FPGA predictions in queue yet.")


    # SLOT: called when FPGA receiver encounters an error
    def _on_fpga_error(self, message: str):
        """Handle FPGA receiver errors"""
        print(f"FPGA Receiver Error: {message}")
        QtWidgets.QMessageBox.critical(self, "FPGA Connection Error", message)


    # FUNCTION: turn mcu offline
    def _offline_mcu(self):
        self._stop_mcu_worker()
        self.mcu_worker = McuWorker(port=self.mcu_port, stage="Offline")
        self.mcu_worker.error.connect(self._on_mcu_error)
        print("Restarting? should be with stage ", "Offline")
        self.mcu_worker.start()
        self._stop_mcu_worker()


    # FUNCTION: clean up resources on window close
    def closeEvent(self, event):
        """Handle application shutdown and cleanup"""
        print("Closing dashboard...")
        
        # Stop MCU worker if running
        if self.mcu_worker is not None:
            self.mcu_worker.stop()
            # Wait for receiver to stop during app close (more time is acceptable here)
            self.mcu_worker.wait(500)  # 500ms timeout for app shutdown
        
        # Stop FPGA receiver if running
        if self.fpga_receiver is not None:
            self.fpga_receiver.stop()
            # Wait for receiver to stop during app close
            self.fpga_receiver.wait(500)  # 500ms timeout for app shutdown
        
        # Stop timers
        # self.timer.stop()
        self.wavelet_update_timer.stop()
        self.prediction_timer.stop()
        if hasattr(self, 'real_data_timer'):
            self.real_data_timer.stop()
        
        event.accept()

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
