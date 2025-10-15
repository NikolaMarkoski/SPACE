import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QOpenGLWidget

from Components.GraphDisplay import GraphDisplay
from Components.TLEDisplay import TLEDisplay
from Components.Backend import Backend
from Components.TimeGlobeWidget import TimeGlobeWidget


#TEMP#
import random #To temporarily select a couple satellites from the 3le file sam posted
from skyfield.constants import ERAD

EARTH_RADIUS = 6378
increment = False

# ————————————————————————————————
#  1) Main Window
# ————————————————————————————————

class MainWindow(QMainWindow):
    
    def __init__(self): 
        super().__init__()
        #Initialize window and place OpengGL inside 
        self.setWindowTitle("S.P.A.C.E")
        self.setGeometry(100, 100, 640, 480)

        self.set_up_backend()

        self.setCentralWidget(TimeGlobeWidget(self.backend))
        
        self.set_up_tle_display()
        
        self.set_up_graph_display()
    
    def set_up_tle_display(self):
        self.tle_display = TLEDisplay(self)
        self.tle_display.raise_()

    def set_up_graph_display(self):
        self.graph_display = GraphDisplay(self)
        self.graph_display.raise_()

    def set_up_backend(self):
        self.backend = Backend()

    #PATCHNOTE: Added ResizeEvent to main window, solved TLEDisplay resize issue
    #TODO: figure out resize update for tleDisplay scoll window
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.tle_display.update_size()
        #self.graph_display.update_height()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_())