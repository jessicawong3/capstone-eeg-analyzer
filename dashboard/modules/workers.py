from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np
from modules.mcu_transfer_pipeline import open_serial, send_stage_command, read_one_sample, mock_read_one_sample, _current_mock_stage
from modules.preprocess import parse_mcu_sample
from modules.pynq_transfer_pipeline import preprocess_and_send
import modules.mcu_transfer_pipeline as mcu_pipeline

MOCK_MCU = True

# Number of samples to collect before emitting one signal to the UI.
# At 256 Hz, CHUNK_SIZE=32 → ~8 UI updates/sec (plenty smooth, low overhead).
CHUNK_SIZE = 32


# Worker thread for preprocessing and uploading an EDF file to the PYNQ board
class DatasetTransferWorker(QThread):

    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, edf_path: str):
        super().__init__()
        self.edf_path = edf_path

    def run(self):
        print("HELLO???")
        try:
            preprocess_and_send(self.edf_path)
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
            token = read_fn()
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
            except Exception as e:
                self.error.emit(f"Could not open serial port {self.port}:\n{e}")
                return

            try:
                send_stage_command(ser, self.stage)
            except Exception as e:
                self.error.emit(f"Could not send stage command: {e}")
                ser.close()
                return

            while self._running and self.stage != "Offline":
                chunk = self._collect_chunk(lambda: read_one_sample(ser))
                if chunk is not None:
                    self.chunk_ready.emit(chunk)

            ser.close()

    def stop(self):
        """Signal the worker loop to exit."""
        self._running = False
