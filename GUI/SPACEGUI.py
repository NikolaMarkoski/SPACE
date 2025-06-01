import sys
import numpy as np
from PyQt5.QtCore import Qt, QTime, QTimer
from PyQt5.QtGui import QFontDatabase, QFont, QSurfaceFormat, QImage
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QOpenGLWidget
)
from OpenGL.GL import *
from OpenGL.GLU import *

import math
import datetime

EARTH_RADIUS = 6378
increment = False

class Satellites(QOpenGLWidget):
    #Bugs in this class:
    #1. Orbit doesn't align with the satellites. I've tried to make it work, but it doesn't.
    #2. Some satellites in the SATTLE.txt have positions that are 40,000,000km from earth, which don't make sense.
    #3. Time hasn't been included in this yet
    #
    #
    def __init__(self):
        self.satellites = {}
        self.read_file()
        self.time = 0
        self.position = 0
        self.quadric = None
        
    def Quadric(self, quad=None):
        if quad != None:
            self.quadric = quad
        else:
            return self.quadric
        
    #Temp function just for visual. Need to update this gui to get one main loop
    def read_file(self):
        input_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), r"TLEs\SATTLE.txt")
        satellites = load.tle_file(input_file)
        if not satellites:
            print("No TLE Data Found")
            return
    
        satDict = {}
        for sat in satellites:
            satnum = sat.model.satnum
            if satnum != 19274 and satnum != 7924: continue
            if satnum not in satDict.keys():
                satDict[satnum] = []
            #Restricts Dictionary to 10 Positions, best to remove in the future
            if len(satDict[satnum]) > 10:
                continue
            satDict[satnum].append(sat)
       
        self.satellites = satDict
        
    def SatDraw(self):
        self.DrawSatellites()
        self.DrawOrbits()
        
    def tempColor(self, satnum):
        #Color to differentiate satellites
        r = (satnum // 10000)/100
        g = ((satnum // 100) % 100)/100
        b = (satnum % 100)/100
        glColor3f(r,g,b)
        
    def getXYZ(self, position):
        geocentric = position.at(load.timescale().utc(self.time)).position.km
        x,y,z = (pos/EARTH_RADIUS for pos in geocentric)
        return x,y,z
            
    def DrawSatellites(self, sphere_radius=0.05):
        for satnum,positions in self.satellites.items():
            x,y,z = self.getXYZ(positions[self.position])
            self.tempColor(satnum)
            glPushMatrix()
            glTranslatef(x,y,z)
            gluSphere(self.quadric, sphere_radius, 40, 40)
            glPopMatrix()
            
    def CalculateOrbit(self, p1, p2):
        #Doesn't work :(
        def normalize(v):
            norm = np.linalg.norm(v)
            return v / norm if norm != 0 else v
        p1 = np.array(p1, dtype=np.float64)
        p2 = np.array(p2, dtype=np.float64)

        center = (p1 + p2) / 2
        vec = p2 - p1

        # Find normal of the disk plane
        arbitrary = np.array([1, 0, 0]) if abs(vec[0]) < 0.9 else np.array([0, 1, 0])
        tangent = normalize(np.cross(vec, arbitrary))
        normal = normalize(np.cross(vec, tangent))

        # Compute rotation from [0,0,1] (XY disk normal) to this normal
        from_vec = np.array([0, 0, 1])
        to_vec = normal
        axis = normalize(np.cross(from_vec, to_vec))
        dot = np.clip(np.dot(from_vec, to_vec), -1.0, 1.0)
        angle = np.degrees(np.arccos(dot))

        if np.linalg.norm(axis) < 1e-6:
            axis = np.array([1, 0, 0])  # arbitrary axis if vectors are parallel or anti-parallel

        radius = np.linalg.norm(vec) / 2

        return center, normal, axis, angle, radius

    def DrawOrbits(self):
        for satnum,positions in self.satellites.items():
            center, normal, axis, angle, radius = self.CalculateOrbit(self.getXYZ(positions[self.position]), self.getXYZ(positions[self.position+1]))
            self.tempColor(satnum)
            glPushMatrix()
            glRotatef(angle*180/math.pi, *axis)
            glRotatef(angle*180/math.pi, *normal)
            gluDisk(self.quadric, 1.28, 1.3, 40, 1)
            glPopMatrix()


# ————————————————————————————————
#  1) OpenGL Globe
# ————————————————————————————————
class GlobeWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.xRot = 0.0
        self.yRot = 90.0  # Start with prime meridian facing front
        self.zRot = 0.0
        self.quadric = None
        self.textureID = 0

        self.satellites = Satellites()

    def initializeGL(self):
        glClearColor(0.2, 0.3, 0.3, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)

        self.textureID = self.loadTexture("Earth.png")
        if not self.textureID:
            glDisable(GL_TEXTURE_2D)
        else:
            print(f"[OK] Texture loaded. ID: {self.textureID}")

        # Flip texture vertically
        glMatrixMode(GL_TEXTURE)
        glLoadIdentity()
        glScalef(1.0, -1.0, 1.0)  # Flip vertically
        glMatrixMode(GL_MODELVIEW)

        self.quadric = gluNewQuadric()
        gluQuadricTexture(self.quadric, GL_TRUE)
        
        self.satellites.Quadric(self.quadric)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, self.width() / (self.height() or 1), 1.0, 100.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

    def loadTexture(self, path):
        img = QImage(path)
        if img.isNull():
            print(f"[Warning] Failed to load texture: {path}")
            return 0

        img = img.convertToFormat(QImage.Format_RGBA8888)
        w, h = img.width(), img.height()
        ptr = img.bits()
        ptr.setsize(img.byteCount())
        arr = np.array(ptr, dtype=np.uint8).reshape(h, w, 4)

        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, arr)
        glBindTexture(GL_TEXTURE_2D, 0)
        return tex

    def drawCone(self, radius, height, num_slices):
        glBegin(GL_TRIANGLE_FAN)
        glColor4f(1.0, 0.5, 0.0, 0.5)  # Transparent orange
        glVertex3f(0, height / 2, 0)
        for i in range(num_slices + 1):
            angle = i * (2.0 * np.pi) / num_slices
            x = radius * np.cos(angle)
            z = radius * np.sin(angle)
            glVertex3f(x, -height / 2, z)
        glEnd()

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Position the camera
        gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)

        # FIX 1: Align poles vertically (Z → Y)
        glRotatef(-90, 1, 0, 0)  # Rotate globe forward so poles face up/down

        # FIX 2: Rotate east–west around vertical (Z now acts as vertical)
        glRotatef(self.yRot, 0, 0, 1)

        # Draw Earth (opaque)
        if self.textureID:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.textureID)

        glColor4f(1.0, 1.0, 1.0, 1.0)  # Ensure Earth is fully opaque
        gluSphere(self.quadric, 1.0, 40, 40)

        if self.textureID:
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)

        # Draw transparent cone
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_FALSE)
        self.drawCone(radius=1.5, height=2.0, num_slices=40)
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)
        
        self.satellites.SatDraw()


# ————————————————————————————————
#  2) Time + Globe + Slider UI
# ————————————————————————————————
class TimeGlobeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.time = QTime.currentTime()

        self.welc_lbl     = QLabel("Welcome to S.P.A.C.E.")
        self.time_lbl     = QLabel(self.time.toString("hh:mm:ss"))
        self.start_btn    = QPushButton("Start")
        self.stop_btn     = QPushButton("Stop")
        self.now_btn      = QPushButton("Now")
        self.midnight_btn = QPushButton("Midnight")
        self.globe        = GlobeWidget()
        self.slider       = QSlider(Qt.Horizontal)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)

        self._buildUI()

    def _buildUI(self):
        font_id = QFontDatabase.addApplicationFont("A-Space Regular Demo.otf")
        fams = QFontDatabase.applicationFontFamilies(font_id)
        base = QFont(fams[0], 24) if fams else QFont("Arial", 24)
        self.welc_lbl.setFont(base)
        self.time_lbl.setFont(base)

        self.slider.setRange(0, 360)
        self.slider.setValue(90)  # Start with Earth facing front
        self.slider.setTickInterval(30)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.valueChanged.connect(self.onSlider)

        v = QVBoxLayout(self)
        v.addWidget(self.welc_lbl, alignment=Qt.AlignHCenter)
        v.addWidget(self.time_lbl, alignment=Qt.AlignHCenter)

        h = QHBoxLayout()
        for btn in (self.start_btn, self.stop_btn, self.now_btn, self.midnight_btn):
            h.addWidget(btn)
        v.addLayout(h)

        v.addWidget(self.globe, stretch=1)
        v.addWidget(self.slider)

        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        self.now_btn.clicked.connect(self.now)
        self.midnight_btn.clicked.connect(self.midnight)

        self.now()
        self.start()

    def _tick(self):
        self.time = self.time.addSecs(1)
        self.time_lbl.setText(self.time.toString("hh:mm:ss"))

    def onSlider(self, value):
        self.globe.yRot = float(value)
        self.globe.update()

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def now(self):
        self.timer.stop()
        self.time = QTime.currentTime()
        self.time_lbl.setText(self.time.toString("hh:mm:ss"))
        self.timer.start()

    def midnight(self):
        self.timer.stop()
        self.time = QTime(0, 0, 0)
        self.time_lbl.setText(self.time.toString("hh:mm:ss"))

# ————————————————————————————————
#  3) Main Window
# ————————————————————————————————
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("S.P.A.C.E.")
        self.resize(1280, 720)
        self.setCentralWidget(TimeGlobeWidget())

# ————————————————————————————————
#  4) Application Entry
# ————————————————————————————————
if __name__ == "__main__":
    fmt = QSurfaceFormat()
    fmt.setVersion(2, 1)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
