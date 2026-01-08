from PyQt5.QtCore import QThread
from modules.transfer_pipeline import preprocess_and_send

class DatasetTransferWorker(QThread):
    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        preprocess_and_send(self.path)
