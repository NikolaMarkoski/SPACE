"""
Filename: DropLabel.py
Author: Luke Magnuson
Description: This script serves as a way for the user to supply TLE files.
It supplies a signal when the user drops a file, which contains the file path of the dropped file.
"""
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, pyqtSignal

class DropLabel(QLabel):
    fileDropped = pyqtSignal(str)  # Emits TLE content string
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setText("Drop\nHere")
        self.setAccessibleName("Drop Label")
        self.setFixedSize(100, 100)
        self.setStyleSheet("""
            border: 2px dashed #888;
            border-radius: 6px;
            background-color: #f8f8f8;
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet("""
                QLabel {
                    border: 2px dashed #00aaff;
                    background-color: #e0f7ff;
                    padding: 20px;
                    font-size: 14px;
                }
            """)
        else:
            event.ignore()

    def dropEvent(self, event):
        print("DropLabel - file dropped")
        self.resetStyle()
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(".txt") or file_path.endswith(".tle"):
                with open(file_path, "r") as file:
                    print("DropLabel - Emit")
                    self.fileDropped.emit(file_path)
                break

    def dragLeaveEvent(self, event):
        self.resetStyle()

    def resetStyle(self):
        self.setStyleSheet("""
            border: 2px dashed #888;
            border-radius: 6px;
            background-color: #f8f8f8;
        """)