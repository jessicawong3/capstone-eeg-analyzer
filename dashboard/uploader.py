from PyQt5 import QtWidgets, QtCore, QtGui
import os
from modules.workers import DatasetTransferWorker


# --- UPLOAD PROGRESS DIALOG ---
class UploadProgressDialog(QtWidgets.QDialog):
    def __init__(self, eeg_path: str, fpga_receiver=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Uploading to PYNQ")
        self.setModal(True)
        self.setFixedSize(360, 140)
        # Prevent the user from closing it manually with the X button
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)

        self._spinner_angle = 0
        self._current_stage = "uploading"  # Track what stage we're in
        self._fpga_receiver = fpga_receiver

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
        self._worker.upload_complete.connect(self._on_upload_complete)
        self._worker.finished.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.start()

        # Connect to FPGA receiver's connection signal if available
        if self._fpga_receiver:
            self._fpga_receiver.fpga_connected.connect(self._on_fpga_connected)
            self._fpga_receiver.first_data_received.connect(self._on_first_data_received)

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


    # FUNCTION: show user upload success indication, then transition to FPGA processing
    def _on_upload_complete(self):
        """Called when file upload to PYNQ is complete, before FPGA processing starts."""
        self._current_stage = "processing"
        
        # Show a checkmark
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
        self._status.setText("Upload complete!\nEstablishing connection to FPGA...")
        
        # Restart the spinner animation for FPGA processing phase
        self._anim_timer.start(50)


    # FUNCTION: handle FPGA connection
    def _on_fpga_connected(self, addr):
        """Called when FPGA connects via TCP"""
        print(f"FPGA connected from {addr}")
        self._status.setText(f"FPGA connected!\nReceiving data...")


    # FUNCTION: handle first data received
    def _on_first_data_received(self):
        """Called when first data is received from FPGA"""
        self._anim_timer.stop()
        
        # Show a checkmark
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
        self._status.setText("Data ready!")

        # Close automatically after 1.0 s so the user can see the confirmation
        QtCore.QTimer.singleShot(1000, self.accept)


    # FUNCTION: show user success indication after FPGA processing completes
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
        self._status.setText("Processing complete!")

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
    
