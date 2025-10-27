import sys
import numpy as np
from PyQt5.QtCore import Qt, QTime, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt5.QtGui import QFontDatabase, QFont, QSurfaceFormat, QImage
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QOpenGLWidget, QRadioButton, QTimeEdit
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
         # Time Window
         
        start_time = 0
        end_time = Seconds_Per_Day
        self.timeedit_lbl = QLabel("Set Time Frame (24hr)")
        self.start_tf = QTimeEdit(self)
        self.end_tf   = QTimeEdit(self)
        self.timeedit_btn = self.style_button(QPushButton("Change Time Frame"), 10)
        self.timeedit_btn.clicked.connect(self.edit_time)

        for w in (self.start_tf, self.end_tf):
            w.setDisplayFormat("HH:mm")             
            w.setMinimumTime(QTime(0, 0))
            w.setMaximumTime(QTime(23, 59))
            w.setAccelerated(True)    

        self.slider = self.style_slider(QSlider(Qt.Horizontal))
        self.slider.setRange(start_time, end_time)
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
        self.play_btn = self.style_button(QPushButton("▶"), 20)
        self.play_btn.clicked.connect(self.scroll)
        # Stop Button
        self.stop_btn = self.style_button(QPushButton("Stop"), 20)
        self.stop_btn.clicked.connect(self.stop)
        # Start Button
        self.start_btn    = self.style_button(QPushButton("Start"), 20)
        self.start_btn.clicked.connect(self.start)
        # Current Time Button
        self.now_btn      = self.style_button(QPushButton("Now"), 20)
        self.now_btn.clicked.connect(self.now)
        # Reset Button
        self.midnight_btn = self.style_button(QPushButton("Midnight"), 20)
        self.midnight_btn.clicked.connect(self.midnight)

        # Speed Controls
       
        self.onex_radiobtn = QRadioButton("1x")
        self.onex_radiobtn.setGeometry(QRect(180, 120, 95, 20))
        self.onex_radiobtn.setChecked(True)
        self.twox_radiobtn = QRadioButton("2x")
        self.twox_radiobtn.setGeometry(QRect(180, 120, 95, 20))
        self.threex_radiobtn = QRadioButton("3x")
        self.twox_radiobtn.setGeometry(QRect(180, 120, 95, 20))

        # Layout
        layout.addWidget(self.globe)
        layout.addWidget(self.clock_container)
        layout.addWidget(self.slider)
        self.setLayout(layout)
        h = QHBoxLayout()

        animcont = QHBoxLayout()
        for w in (self.onex_radiobtn, self.twox_radiobtn, self. threex_radiobtn):
            animcont.addWidget(w)
        settings = QVBoxLayout()
        for w in (self.timeedit_lbl, self.start_tf, self.end_tf, self.timeedit_btn):
            settings.addWidget(w)
        settings.addLayout(animcont)
        h.addLayout(settings)

        for btn in (self.play_btn, self.start_btn, self.stop_btn, self.now_btn, self.midnight_btn):
            h.addWidget(btn)
        h.addLayout(settings)
        layout.addLayout(h)

        
    # Animations Controls
        self.anim = QPropertyAnimation(self.slider, b"value", self)
        self.anim.setEasingCurve(QEasingCurve.Linear)
        self.anim.setDuration(Rot_Dur) #Orbit duration
        
        self.setFocusPolicy(Qt.StrongFocus)
        
    def update(self):
        Backend().on_slider_change(self.time.msecsSinceStartOfDay()//1000)

    # Time Controls
    # Updates display clock every second
    def tick(self):
        #print(self.time.msecsSinceStartOfDay()//1000)
        clocktime = self.time.msecsSinceStartOfDay() //1000
        if (clocktime) < (self.slider.maximum()):
            self.time = self.time.addSecs(1)
            self.time_display.setText(self.time.toString("hh:mm:ss"))
            self.time_display.setAccessibleDescription(self.time.toString("hh:mm:ss"))
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
        self.update()

    def midnight(self):
        self.timer.stop()
        self.time = QTime(0, 0, 0)
        self.slider.setValue(0)
        self.time_display.setText(self.time.toString("hh:mm:ss"))
        self.update()

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
        self.update()

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

    def edit_time(self):
        self.slider.setRange((self.start_tf.time().msecsSinceStartOfDay() // 1000),(self.end_tf.time().msecsSinceStartOfDay() // 1000))
        print(self.start_tf.time(), self.end_tf.time())
        print((self.start_tf.time().msecsSinceStartOfDay() // 1000),(self.end_tf.time().msecsSinceStartOfDay() // 1000))
        print(self.slider.maximum())

        
    def keyPressEvent(self, event):
        match event.text().lower():
            case 'n':
                self.now()
            case 'm':
                self.midnight()
            case ' ':
                if self.timer.isActive():
                    self.timer.stop()
                else:
                    self.timer.start()

    #---------------------------------------------------------------
# Styling

    def style_button(self, btn, size):
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(36)
        self.btn_font = QFont("Arial", size)
        btn.setFont(self.btn_font)
        btn.setStyleSheet("""
            QPushButton {
                background: #3A86FF;
                color: #FFFFFF;
                border: 1px solid #2A6FD6;
                border-radius: 8px;
                padding: 6px 12px;
               
            }
            QPushButton:hover   { background: #4F95FF; }
            QPushButton:pressed { background: #2A6FD6; }
            QPushButton:disabled{
                background: #D9E6FF;
                color: #8AA9E6;
                border-color: #BFD2FF;
            }
        """)
        return btn

    def style_slider(self, slider):
        slider.setCursor(Qt.PointingHandCursor)
        slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #E6EAF2;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #3A86FF;
                border-radius: 3px;
            }
            QSlider::add-page:horizontal {
                background: #E6EAF2;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 1px solid #2A6FD6;
                width: 16px;
                margin: -5px 0;   /* centers thumb on 6px track */
                border-radius: 8px;
            }
        """)
        return slider
