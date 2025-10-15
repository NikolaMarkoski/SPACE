import sys
import numpy as np
from PyQt5.QtCore import Qt, QTime, QTimer, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFontDatabase, QFont, QSurfaceFormat, QImage
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QOpenGLWidget
)
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QWidget, QFrame, QGraphicsOpacityEffect, QLineEdit

import math
import datetime
import os
import skyfield
from skyfield.api import load
from skyfield.api import Timescale
from skyfield.api import EarthSatellite

from Components.GlobeWidget import GlobeWidget
from Components.Backend import Backend

Seconds_Per_Day = 24 * 60 *60
Earth_Degrees = 360
Seconds_Per_Degree = Seconds_Per_Day / 360
Rot_Dur = 4000 #Aninmation speed in miliseconds

def degrees_to_sec(deg: int):
    return int(deg * Seconds_Per_Degree) % Seconds_Per_Day

def seconds_to_degrees(s: int):
    s = s % Seconds_Per_Day
    return int(s / Seconds_Per_Degree)

class TimeGlobeWidget(QWidget):
    def __init__(self, backend):
        super().__init__()

        self.backend = backend

        self.setWindowTitle("Clock Display")
        self.setGeometry(100, 100, 800, 400)

        font = QFont('Arial', 48, QFont.Bold)

        layout = QVBoxLayout()

        self.globe = GlobeWidget(self.backend)

        self.backend.subscribe(self.onDataChanged)
        
        # Container for Clock
        self.clock_container = QWidget()
        self.clock_container.setMaximumHeight(100)
        self.clock_container.setAccessibleName("clock_Time")
        self.clock_layout = QVBoxLayout(self.clock_container)
        self.clock_layout.setContentsMargins(0, 0, 0, 0)
        
        # Clock Display
        self.time_display = QLineEdit(self)
        self.time_display.setReadOnly(True)  # Prevent edits
        self.time_display.setAlignment(Qt.AlignCenter)
        self.time_display.setFont(font)
        self.time_display.setStyleSheet("border: none; background: transparent;")  # look like QLabel
        
        self.clock_layout.addWidget(self.time_display)

        # Accessibility for testing automation
        self.time_display.setAccessibleName("clock_Time")
        self.time_display.setAccessibleDescription(QTime.currentTime().toString("hh:mm:ss"))


         # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, Seconds_Per_Day)
        self.slider.setValue(90)  
        self.slider.setTickInterval(30)
        self.slider.setTickPosition(QSlider.TicksBelow)
        self.slider.setAccessibleName("slider_Time")
        self.slider.valueChanged.connect(self.onSlider)

        # Timer that updates clock
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)
        self.now()
        self.start()



        # Play button
        self.play_btn = QPushButton("▶")
        self.play_btn.clicked.connect(self.scroll)
        # Stop Button
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop)
        # Start Button
        self.start_btn    = QPushButton("Start")
        self.start_btn.clicked.connect(self.start)
        # Current Time Button
        self.now_btn      = QPushButton("Now")
        self.now_btn.clicked.connect(self.now)
        # Reset Button
        self.midnight_btn = QPushButton("Midnight")
        self.midnight_btn.clicked.connect(self.midnight)


        # Layout
        layout.addWidget(self.globe)
        layout.addWidget(self.clock_container)
        layout.addWidget(self.slider)
        self.setLayout(layout)
        h = QHBoxLayout()
        for btn in (self.play_btn, self.start_btn, self.stop_btn, self.now_btn, self.midnight_btn):
            h.addWidget(btn)
        layout.addLayout(h)
        

    # Animations Controls
        self.anim = QPropertyAnimation(self.slider, b"value", self)
        self.anim.setEasingCurve(QEasingCurve.Linear)
        self.anim.setDuration(Rot_Dur) #Orbit duration
        
    def update(self):
        Backend().on_slider_change(self.slider.value())

    # Time Controls
    # Updates display clock every second
    def tick(self):
        self.time = self.time.addSecs(1)
        self.time_display.setText(self.time.toString("hh:mm:ss"))
        self.time_display.setAccessibleDescription(self.time.toString("hh:mm:ss"))
        self.slider.setValue((QTime(0,0).secsTo(self.time)))
        self.update()

    def start(self):
        self.timer.start()

    def now(self):
        self.timer.stop()
        self.time = QTime.currentTime()
        self.time_display.setText(self.time.toString("hh:mm:ss"))
        self.slider.blockSignals(True)
        self.slider.setValue((QTime(0, 0).secsTo(self.time)))
        self.slider.blockSignals(False)
        self.timer.start()

    def midnight(self):
        self.timer.stop()
        self.time = QTime(0, 0, 0)
        self.slider.setValue(0)
        self.time_display.setText(self.time.toString("hh:mm:ss"))

    def stop(self):
        self.timer.stop()
        self.anim.stop()

    # Slider Controls
    def onSlider(self, value):
        print(seconds_to_degrees(value))
        self.timer.stop()
        self.time = QTime(0,0).addSecs(value)
        self.time_display.setText(self.time.toString("hh:mm:ss"))
        self.timer.start()
        self.globe.yRot = float(value/240)
        self.globe.update()

    def update_display_and_slider(self):
        self.time_display.setText(self.time.toString("hh:mm:ss"))
        self.time_display.setAccessibleDescription(self.time.toString("hh:mm:ss"))
        self.slider.blockSignals(True)
        self.slider.setValue(degrees_to_sec(QTime(0,0).secsTo(self.time)))
        self.slider.blockSignals(True)

    def onDataChanged(self):
        self.globe.update()


    def scroll(self):
        self.anim.stop()
        self.anim.setStartValue(self.slider.value())
        self.anim.setEndValue(self.slider.maximum())
        self.anim.start()