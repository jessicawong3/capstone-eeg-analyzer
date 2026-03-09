from PyQt5 import QtWidgets, QtCore, QtGui
import os
from modules.workers import DatasetTransferWorker


# --- UPLOAD PROGRESS DIALOG ---
class UploadProgressDialog(QtWidgets.QDialog):
    def __init__(self, eeg_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Uploading to PYNQ")
        self.setModal(True)
        self.setFixedSize(360, 140)
        # Prevent the user from closing it manually with the X button
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)

        self._spinner_angle = 0

        # Spinner canvas
        self._spinner_label = QtWidgets.QLabel()
        self._spinner_label.setFixedSize(40, 40)
        self._spinner_label.setAlignment(QtCore.Qt.AlignCenter)

        # Status text
        filename = os.path.basename(eeg_path)
        self._status = QtWidgets.QLabel(f"Uploading  {filename}…")
        self._status.setWordWrap(True)
        self._status.setAlignment(QtCore.Qt.AlignCenter)

        row = QtWidgets.QHBoxLayout()
        row.addStretch()
        row.addWidget(self._spinner_label)
        row.addStretch()

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addStretch()
        layout.addLayout(row)
        layout.addWidget(self._status)
        layout.addStretch()

        # Animate the spinner using a timer
        self._anim_timer = QtCore.QTimer(self)
        self._anim_timer.timeout.connect(self._tick_spinner)
        self._anim_timer.start(50)  # ~20 fps

        # Worker
        self._worker = DatasetTransferWorker(eeg_path)
        self._worker.finished.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.start()

        self._error_msg = None


    # FUNCTION: draw spinner
    def _tick_spinner(self):
        self._spinner_angle = (self._spinner_angle + 18) % 360
        size = 36
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        pen = QtGui.QPen(QtGui.QColor("#a9a9a9"), 4)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.translate(size / 2, size / 2)
        painter.rotate(self._spinner_angle)
        painter.drawArc(-14, -14, 28, 28, 60 * 16, 270 * 16)
        painter.end()
        self._spinner_label.setPixmap(pixmap)


    # FUNCTION: show user success indication
    def _on_success(self):
        self._anim_timer.stop()

        # Show a checkmark and confirmation text briefly before closing
        success_pixmap = QtGui.QPixmap(36, 36)
        success_pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(success_pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setPen(QtGui.QPen(QtGui.QColor("#16a34a"), 3, QtCore.Qt.SolidLine,
                                  QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
        painter.drawLine(6, 18, 14, 26)
        painter.drawLine(14, 26, 30, 10)
        painter.end()
        self._spinner_label.setPixmap(success_pixmap)
        self._status.setText("Upload complete")

        # Close automatically after 1.2 s so the user can see the confirmation
        QtCore.QTimer.singleShot(1200, self.accept)


    # FUNCTION: show user error indication
    def _on_error(self, message: str):
        self._anim_timer.stop()
        self._error_msg = message
        self.reject()   # closes dialog, returns QDialog.Rejected


    # FUNCTION: get error message
    def error_message(self) -> str:
        return self._error_msg or ""
    



# class DatasetUploader(QtWidgets.QWidget):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("EEG Dataset Uploader")
#         self.resize(400, 250)


#         # --- TITLE ---
#         self.subtitle = QtWidgets.QLabel(
#             "Prepare and transfer EEG datasets to the PYNQ board."
#         )
#         self.subtitle.setWordWrap(True)
#         self.subtitle.setAlignment(QtCore.Qt.AlignCenter)


#         # --- CONTROLS ---
#         self.load_button = QtWidgets.QPushButton("Select EDF File to Upload")
#         self.load_button.setToolTip("Choose an EDF file to send to the PYNQ board")
#         self.load_button.setFixedHeight(40)
#         # self.load_button.setMaximumWidth(300)
#         # self.load_button.setAlignment(QtCore.Qt.AlignCenter)



#         # --- STATUS ---
#         self.status_label = QtWidgets.QLabel("Status: Waiting for file selection")
#         self.status_label.setObjectName("StatusLabel")
#         self.status_label.setWordWrap(True)
#         self.status_label.setAlignment(QtCore.Qt.AlignCenter)


#         # --- LAYOUT ---
#         content_layout = QtWidgets.QVBoxLayout()
#         content_layout.setSpacing(16)
#         # content_layout.setAlignment(QtCore.Qt.AlignCenter)

#         content_layout.addWidget(self.subtitle)
#         content_layout.addSpacing(10)
#         content_layout.addWidget(self.load_button)
#         content_layout.addWidget(self.status_label)

#         main_layout = QtWidgets.QVBoxLayout()
#         main_layout.addStretch()
#         main_layout.addLayout(content_layout)
#         main_layout.addStretch()

#         self.setLayout(main_layout)


#         # --- SIGNALS ---
#         self.load_button.clicked.connect(self.load_data)




#     def load_data(self):
#         paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
#             self, "Open EEG EDF", "", "EDF Files (*.edf)"
#         )

#         if not paths:
#             return
        
#         self.path_queue = list(paths)
#         self.curr_upload = 1
#         self.total_uploads = len(paths)
#         self.load_button.setEnabled(False)
#         self.next_upload()

    

#     def next_upload(self):
#         if not self.path_queue:
#             self.all_uploads_finished()
#             return

#         path = self.path_queue.pop(0)
#         self.status_label.setText(f"Status: Processing and uploading dataset… ({self.curr_upload}/{self.total_uploads})")
#         self.transfer_worker = DatasetTransferWorker(path)
#         self.transfer_worker.finished.connect(self.upload_finished)
#         self.transfer_worker.error.connect(self.upload_error)
#         self.transfer_worker.start()


    
#     def upload_finished(self):
#         self.curr_upload += 1
#         self.next_upload()



#     def upload_error(self, message: str):
#         self.status_label.setText(f"Status: Error — {message}")
#         self.load_button.setEnabled(True)
#         QtWidgets.QMessageBox.critical(self, "Upload Failed", message)



#     def all_uploads_finished(self):
#         self.status_label.setText("Status: Upload complete ✔")
#         self.load_button.setEnabled(True)



# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)

#     try:
#         with open("./styles.qss", "r") as f:
#             app.setStyleSheet(f.read())
#     except FileNotFoundError:
#         pass

#     win = DatasetUploader()
#     win.show()
#     sys.exit(app.exec_())
