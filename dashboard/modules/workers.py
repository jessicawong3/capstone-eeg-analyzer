from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np
from modules.mcu_transfer_pipeline import open_serial, send_stage_command, read_one_sample, mock_read_one_sample, _current_mock_stage
from modules.preprocess import parse_mcu_sample
from modules.pynq_transfer_pipeline import preprocess_and_send, signal_fpga_process_file, stop_fpga_processing
import modules.mcu_transfer_pipeline as mcu_pipeline
from modules.tcp.receive import receive_array
from pathlib import Path

MOCK_MCU = False


# Worker thread for stopping FPGA processing
class FPGAStopWorker(QThread):
    """
    Background worker to stop FPGA processing without blocking the UI.
    The stop_fpga_processing() SSH call can block for a long time.
    """
    
    # Emitted when FPGA processing has been stopped
    stopped = pyqtSignal()
    # Emitted when there's an error
    error = pyqtSignal(str)

    def __init__(self, mode: str = "real_data"):
        super().__init__()
        self.mode = mode

    def run(self):
        try:
            print(f"Stopping FPGA {self.mode} mode processing in background thread...")
            stop_fpga_processing(mode=self.mode)
            print("FPGA processing stopped successfully")
            self.stopped.emit()
        except Exception as e:
            # Don't treat stop failures as critical errors - process might not be running
            print(f"FPGA stop notice: {str(e)}")
            self.stopped.emit()


# Worker thread for signaling FPGA to start processing
class FPGAStartWorker(QThread):
    """
    Background worker to start FPGA processing without blocking the UI.
    The signal_fpga_process_file() SSH call can block for a long time.
    """
    
    # Emitted when FPGA processing has been signaled to start
    started = pyqtSignal()
    # Emitted when there's an error
    error = pyqtSignal(str)

    def __init__(self, filename: str, mode: str = "synthetic"):
        super().__init__()
        self.filename = filename
        self.mode = mode

    def run(self):
        try:
            print(f"Signaling FPGA to start {self.mode} mode processing in background thread...")
            stdout, stderr, return_code = signal_fpga_process_file(self.filename, mode=self.mode)
            
            if return_code == 0:
                print("FPGA processing started successfully")
                self.started.emit()
            else:
                error_msg = f"FPGA processing command failed with return code {return_code}"
                if stderr:
                    error_msg += f"\nStderr: {stderr}"
                self.error.emit(error_msg)
        except Exception as e:
            self.error.emit(f"Could not signal FPGA: {str(e)}")
            print(f"Error: {e}")

# Number of samples to collect before emitting one signal to the UI.
# At 256 Hz, CHUNK_SIZE=32 → ~8 UI updates/sec (plenty smooth, low overhead).
CHUNK_SIZE = 32


# Worker thread for preprocessing and uploading an EDF file to the PYNQ board
class DatasetTransferWorker(QThread):

    # Emitted when file upload to PYNQ is complete
    upload_complete = pyqtSignal()
    # Emitted when FPGA processing is complete
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, edf_path: str, pynq_host: str = "127.0.0.1", mode: str = "real_data"):
        super().__init__()
        self.edf_path = edf_path
        self.pynq_host = pynq_host
        self.mode = mode

    def run(self):
        try:
            print(f"Starting dataset transfer with file {self.edf_path} in {self.mode} mode...")
            # Preprocess and send the file
            preprocess_and_send(self.edf_path)

            # Signal that upload is complete
            self.upload_complete.emit()
            
            # Signal FPGA to start processing the file
            if Path(self.edf_path).suffix == ".edf":
                # EDF file: will be converted to .npz with name_processed.npz
                filename = Path(self.edf_path).stem + "_processed.npz"
            elif Path(self.edf_path).suffix == ".npy":
                # NPY file: convert to .npz format
                just_filename = self.edf_path.split('/')[-1]  # Extract just the filename
                filename = Path(just_filename).with_name(
                    Path(just_filename).stem.replace("-epochs", "") + ".npz"
                )
            else:
                raise ValueError(f"Unsupported file type: {Path(self.edf_path).suffix}")
            
            stdout, stderr, return_code = signal_fpga_process_file(filename, mode=self.mode)
            
            if return_code != 0:
                self.error.emit(f"FPGA processing command failed with code {return_code}\nStderr: {stderr}")
                return
            
            # Signal that processing is complete
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


# Worker thread for taking in synthetic MCU data
class McuWorker(QThread):

    # Emits a numpy array of CHUNK_SIZE preprocessed voltage samples
    chunk_ready = pyqtSignal(object)
    # Emits an error string if the serial port can't be opened
    error = pyqtSignal(str)

    def __init__(self, port: str, stage: str):
        super().__init__()
        self.port = port
        self.stage = stage
        self._running = False
        self._serial = None  # Keep reference to serial port for cleanup

    def set_stage(self, stage: str):
        """Change the current stage without stopping the worker."""
        self.stage = stage
        print(f"MCU Worker stage changed to: {stage}")

    def _collect_chunk(self, read_fn):
        """Read CHUNK_SIZE valid voltage samples using the given read function.
        Returns a numpy float32 array, or None if stopped mid-chunk."""
        buf = np.empty(CHUNK_SIZE, dtype=np.float32)
        count = 0
        while count < CHUNK_SIZE:
            if not self._running:
                return None
            try:
                token = read_fn()
            except Exception:
                # If read fails, check if we're supposed to stop
                if not self._running:
                    return None
                raise
            if token is None:
                continue
            voltage = parse_mcu_sample(token)
            if voltage is not None:
                buf[count] = voltage
                count += 1
        return buf

    def run(self):
        self._running = True
        print("MCU Worker started with stage:", self.stage)

        if MOCK_MCU:
            while self._running and self.stage != "Offline":
                # Keep mock stage in sync with current worker stage
                mcu_pipeline._current_mock_stage = self.stage
                
                chunk = self._collect_chunk(mock_read_one_sample)
                if chunk is not None:
                    self.chunk_ready.emit(chunk)

        else:
            try:
                ser = open_serial(self.port)
                self._serial = ser  # Keep reference for cleanup
            except Exception as e:
                self.error.emit(f"Could not open serial port {self.port}:\n{e}")
                return

            try:
                send_stage_command(ser, self.stage)
            except Exception as e:
                self.error.emit(f"Could not send stage command: {e}")
                ser.close()
                return

            # Track the last stage we sent to the MCU
            last_sent_stage = self.stage

            while self._running and self.stage != "Offline":
                # Check if stage changed and send new command if it did
                if self.stage != last_sent_stage:
                    try:
                        send_stage_command(ser, self.stage)
                        last_sent_stage = self.stage
                    except Exception as e:
                        self.error.emit(f"Could not send stage command: {e}")
                        ser.close()
                        return
                
                chunk = self._collect_chunk(lambda: read_one_sample(ser))
                if chunk is not None:
                    self.chunk_ready.emit(chunk)

            ser.close()
            self._serial = None

    def stop(self):
        """Signal the worker loop to exit and close serial port to interrupt reads."""
        self._running = False
        # Close serial port immediately to interrupt any blocking read
        if self._serial is not None:
            try:
                self._serial.close()
            except Exception:
                pass  # Already closed or error closing
            self._serial = None


# Worker thread for receiving FPGA data over TCP
class FPGAReceiverWorker(QThread):

    # Emits the received EEG array (7, 960) and result array (1, 6)
    data_ready = pyqtSignal(object, object)
    # Emits when FPGA connects (receives address tuple)
    fpga_connected = pyqtSignal(tuple)
    # Emits when first data is received
    first_data_received = pyqtSignal()
    # Emits an error string if connection fails
    error = pyqtSignal(str)

    def __init__(self, host: str = '0.0.0.0', port: int = 9999):
        super().__init__()
        self.host = host
        self.port = port
        self._running = False
        self._first_data_received = False

    def run(self):
        """Run the TCP receiver in a background thread."""
        
        self._running = True
        print(f"FPGA Receiver started on {self.host}:{self.port}")

        def on_data_received(eeg_array, result_array):
            """Callback when data is received from FPGA"""
            print(f"Received EEG {eeg_array.shape} and result {result_array.shape}")
            
            # Emit first_data_received signal only once
            if not self._first_data_received:
                self._first_data_received = True
                print("Emitting first_data_received signal")
                self.first_data_received.emit()
            
            self.data_ready.emit(eeg_array, result_array)

        def on_fpga_connect(addr):
            """Callback when FPGA connects"""
            print(f"Emitting fpga_connected signal for {addr}")
            self.fpga_connected.emit(addr)

        try:
            receive_array(host=self.host, port=self.port, callback=on_data_received, on_connect=on_fpga_connect)
        except Exception as e:
            self.error.emit(f"FPGA Receiver error: {str(e)}")

    def stop(self):
        """Signal the receiver to stop."""
        from modules.tcp.receive import stop
        stop()
        self._running = False

    def reset_first_data_flag(self):
        self._first_data_received = False
        print("FPGA Receiver: Reset first data flag for next mode")

