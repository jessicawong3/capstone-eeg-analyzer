from PyQt5.QtCore import QThread, pyqtSignal
from modules.mcu_transfer_pipeline import open_serial, send_stage_command, read_one_sample
from modules.preprocess import parse_mcu_sample
from modules.pynq_transfer_pipeline import preprocess_and_send


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


# Worker thread for taking in live MCU data
class McuWorker(QThread):

    # Emits one preprocessed float voltage per sample
    sample_ready = pyqtSignal(float)
    # Emits an error string if the serial port can't be opened
    error = pyqtSignal(str)

    def __init__(self, port: str, stage: str):
        super().__init__()
        self.port = port
        self.stage = stage
        self._running = False

    def run(self):
        print("RUNNING MCU WORKER with stage:", self.stage)
        self._running = True
        try:
            ser = open_serial(self.port)
        except Exception as e:
            self.error.emit(f"Could not open serial port {self.port}:\n{e}")
            return

        # Tell the MCU which stage we want
        try:
            send_stage_command(ser, self.stage)
        except Exception as e:
            self.error.emit(f"Could not send stage command: {e}")
            ser.close()
            return

        # Stream samples until stop() is called
        while self._running and self.stage != "Offline":
            token = read_one_sample(ser)
            print("Read one sample")
            if token is not None:
                print("Parsing sample")
                voltage = parse_mcu_sample(token)
                if voltage is not None:
                    print("Emitting sample")
                    self.sample_ready.emit(voltage)

        ser.close()


    def stop(self):
        """Signal the worker loop to exit."""
        self._running = False
