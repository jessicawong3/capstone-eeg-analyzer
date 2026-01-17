from PyQt5 import QtWidgets, QtCore
import sys

from modules.workers import DatasetTransferWorker


class DatasetUploader(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EEG Dataset Uploader")
        self.resize(400, 250)


        # --- TITLE ---
        self.subtitle = QtWidgets.QLabel(
            "Prepare and transfer EEG datasets to the PYNQ board."
        )
        self.subtitle.setWordWrap(True)
        self.subtitle.setAlignment(QtCore.Qt.AlignCenter)


        # --- CONTROLS ---
        self.load_button = QtWidgets.QPushButton("Select EDF File to Upload")
        self.load_button.setToolTip("Choose an EDF file to send to the PYNQ board")
        self.load_button.setFixedHeight(40)
        # self.load_button.setMaximumWidth(300)
        # self.load_button.setAlignment(QtCore.Qt.AlignCenter)



        # --- STATUS ---
        self.status_label = QtWidgets.QLabel("Status: Waiting for file selection")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)


        # --- LAYOUT ---
        content_layout = QtWidgets.QVBoxLayout()
        content_layout.setSpacing(16)
        # content_layout.setAlignment(QtCore.Qt.AlignCenter)

        content_layout.addWidget(self.subtitle)
        content_layout.addSpacing(10)
        content_layout.addWidget(self.load_button)
        content_layout.addWidget(self.status_label)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addStretch()
        main_layout.addLayout(content_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)


        # --- SIGNALS ---
        self.load_button.clicked.connect(self.load_data)




    def load_data(self):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Open EEG EDF", "", "EDF Files (*.edf)"
        )

        if not paths:
            return
        
        self.path_queue = list(paths)
        self.curr_upload = 1
        self.total_uploads = len(paths)
        self.load_button.setEnabled(False)
        self.next_upload()

    

    def next_upload(self):
        if not self.path_queue:
            self.all_uploads_finished()
            return

        path = self.path_queue.pop(0)
        self.status_label.setText(f"Status: Processing and uploading dataset… ({self.curr_upload}/{self.total_uploads})")
        self.transfer_worker = DatasetTransferWorker(path)
        self.transfer_worker.finished.connect(self.upload_finished)
        self.transfer_worker.start()


    
    def upload_finished(self):
        self.curr_upload += 1
        self.next_upload()



    def all_uploads_finished(self):
        self.status_label.setText("Status: Upload complete ✔")
        self.load_button.setEnabled(True)



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    try:
        with open("./styles.qss", "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    win = DatasetUploader()
    win.show()
    sys.exit(app.exec_())
