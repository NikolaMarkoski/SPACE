import sys
import numpy as np
from PyQt5.QtCore import Qt, QTime, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QFontDatabase, QFont, QSurfaceFormat, QImage
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QOpenGLWidget
)
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtWidgets import QPushButton, QVBoxLayout, QWidget, QFrame, QGraphicsOpacityEffect, QLineEdit, QToolTip
from PyQt5.QtGui import QCursor

import math
from datetime import datetime, timezone, timedelta
import os
import skyfield
from skyfield.api import load
from skyfield.api import Timescale
from skyfield.api import EarthSatellite

from .SpaceObjects import SpaceObject, SpaceObjectType, Satellite, GroundStation
from Components.AdjacencyMatrix import AdjacencyMatrix

class GlobeWidget(QOpenGLWidget):
    def __init__(self, backend, parent=None):
        super().__init__(parent)

        self.backend = backend
        self.backend.subscribe(self.updateSpaceObjects)

        self.xRot = 0.0
        self.yRot = 90.0  # Start with prime meridian facing front
        self.zRot = 0.0
        self.quadric = None
        self.textureID = 0

        self.spaceObjects = {}
        self.spaceObjects.update(self.loadGroundStations())
        self.ObjectAdjacencyMatrix = AdjacencyMatrix(backend)
        
        self.setMouseTracking(True)
        self.twoDPoints = []
        self.last_hover = None
        self.last_mouse_pos = None

        self.camRadius = 5.0
        self.camAzimuth = 0.0
        self.camElevation = 0.0

    def initializeGL(self):
        glClearColor(0.2, 0.3, 0.3, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_TEXTURE_2D)

        # Load Textures
        self.textureID = self.loadTexture("GUI/Assets/Earth.png")
        self.bgtextureID = self.loadTexture("GUI/Assets/Background.jpg")
        if not self.textureID:
            glDisable(GL_TEXTURE_2D)
        else:
            print(f"[OK] Texture loaded. ID: {self.textureID}")

        if not self.bgtextureID:
            print("No background texture applied")
        else:
            print(f"[OK] bgTexture loaded. ID: {self.bgtextureID}")

        # Flip texture vertically
        glMatrixMode(GL_TEXTURE)
        glLoadIdentity()
        glScalef(1.0, -1.0, 1.0)  # Flip vertically
        glMatrixMode(GL_MODELVIEW)

        self.quadric = gluNewQuadric()
        gluQuadricTexture(self.quadric, GL_TRUE)

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

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # Position the camera
        eye = self.get_camera_position()
        gluLookAt(*eye, 0, 0, 0, 0, 1, 0)

        # FIX 1: Align poles vertically (Z → Y)
        glRotatef(-90, 1, 0, 0)  # Rotate globe forward so poles face up/down

        glPushMatrix()
        glRotatef(-90,0,0,1)#Rotate earth so orbits and satellites line up with online trackers, almost

        # Draw Earth (opaque)
        if self.textureID:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, self.textureID)

        glColor4f(1.0, 1.0, 1.0, 1.0)  # Ensure Earth is fully opaque
        gluSphere(self.quadric, 1.0, 40, 40)

        if self.textureID:
            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)

        glPopMatrix()

        for obj in self.spaceObjects.values():
            obj.Draw(self.quadric)
        self.ObjectAdjacencyMatrix.DrawConnections(self.spaceObjects.copy())

        self.TwoDPointProjection()

    def loadGroundStations(self):
        lines = '''Alice Springs Ground Station	-23.67009926	133.88499451
                   Svalbard Satellite Station	78.2167	15.3833
                   Kourou Station	5.2364	-52.7686
                   Raisting Earth Station	47.8833	11.1667
                   Elfordstown Earthstation	51.9500	-7.8833
                   Saint Pierre and Miquelon Satellite Station	46.8856	-56.3150
                   Pleumeur-Bodou Ground Station	48.7833	-3.4667
                   Inuvik Ground Station	68.4000	-133.5000
                   South Point Ground Station	19.0167	-155.6667
                   Clewiston Ground Station	26.7333	-81.0333
                   Esrange Ground Station	67.8833	21.0667'''.split("\n")

        groundStations = {}
        for lineNo, line in enumerate(lines):
            name, lat, long = line.strip().split("\t")
            try:
                long = float(long)
                lat = float(lat)
            except:
                print(f'Line {lineNo} where {name} is, results in an error\nEither the latitude or longitude is not a number')

            groundStations[name] = GroundStation(SpaceObjectType.GroundStation, name, long, lat)
        return groundStations
    
    def TwoDPointProjection(self):
        if not self.spaceObjects: return
            
        modelview = glGetDoublev(GL_MODELVIEW_MATRIX)
        projection = glGetDoublev(GL_PROJECTION_MATRIX)
        viewport = glGetIntegerv(GL_VIEWPORT)

        twoDPoints = []

        #SpaceObjects
        for obj in self.spaceObjects.values():
            x, y, z = obj.position
            sx, sy, sz = gluProject(x, y, z, modelview, projection, viewport)
            sy = viewport[3] - sy
            twoDPoints.append((sx, sy, sz, obj))

        #Globe
        x,y,z = 0,0,0
        sx,sy,sz = gluProject(x, y, z, modelview, projection, viewport)
        sy = viewport[3] - sy
        twoDPoints.append((sx,sy,sz,"Globe"))

        self.twoDPoints = twoDPoints.copy()

    #Mouse Stuff
    def getCurrentSatellite(self, x, y):
        closest_point = None
        min_depth = float("inf")

        for sx, sy, sz, sat in self.twoDPoints:
            if sat == "Globe": continue
            #Temporary fix, sz checks if the satellite is closer to the camera than the earth, but this partially works as satellites can be visible but be further. And also this assumes the camera acts on the same axis.
            radius = self.height() * sat.sphereRadius * sz
            if abs(x - sx) <= radius and abs(y - sy) <= radius and sz < self.twoDPoints[-1][2]:
                if sz < min_depth:
                    min_depth = sz
                    closest_point = sat
        return closest_point


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = event.pos()
        if event.button() == Qt.RightButton:
            currentSatellite = self.getCurrentSatellite(event.x(), event.y())
            if currentSatellite:
                currentSatellite.showOrbit ^= True
            self.update()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_mouse_pos = None

    def mouseMoveEvent(self, event):
        x = event.x()
        y = event.y()

        if self.twoDPoints and self.last_mouse_pos is None:
            closest_point = self.getCurrentSatellite(x,y)

            if self.last_hover and closest_point != self.last_hover: self.last_hover.hover = False

            if closest_point and closest_point != "Globe" and closest_point.show:
                self.last_hover = closest_point
                closest_point.hover = True
                sx,sy,_ = closest_point.position
                globalPos = self.mapToGlobal(QPoint(int(sx),int(sy)))
                QToolTip.showText(QCursor.pos(), f"{closest_point.name}", self)
                self.update()
            else:
                QToolTip.hideText()

        if self.last_mouse_pos is not None:
            dx = event.x() - self.last_mouse_pos.x()
            dy = event.y() - self.last_mouse_pos.y()

            # Sensitivity
            self.camAzimuth -= dx * 0.5
            self.camElevation += dy * 0.5

            # Clamp elevation to avoid flipping
            self.camElevation = max(-89, min(89, self.camElevation))

            self.last_mouse_pos = event.pos()
            self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        zoom_speed = 1.1
        if delta > 0:
            self.camRadius /= zoom_speed  # zoom in
        else:
            self.camRadius *= zoom_speed  # zoom out
        
        self.update()  # redraw the OpenGL scene

    def get_camera_position(self):
        # Convert spherical to Cartesian
        az = math.radians(self.camAzimuth)
        el = math.radians(self.camElevation)

        x = self.camRadius * math.cos(el) * math.sin(az)
        y = self.camRadius * math.sin(el)
        z = self.camRadius * math.cos(el) * math.cos(az)
        return x, y, z

    #for debugging Purposes
    def drawXYZLines(self):
        glPushMatrix()
        glRotatef(90, 1,0,0)
        glBegin(GL_LINES)

        length = 10
        # X-axis (red)
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(length, 0.0, 0.0)
    
        # Y-axis (green)
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, length, 0.0)
    
        # Z-axis (blue)
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 0.0, length)
        
        glEnd()
        glPopMatrix()

    def updateSpaceObjects(self):
        tle_data = self.backend.tle_dict
        tle_status = self.backend.tle_status
        if not tle_data and not tle_status:
            print("Null passed")
            return
        
        print(f"SATELLITES - passed in {len(tle_data)} items")
        #Add new satellites
        for key, lines in tle_data.items():
            if key not in self.spaceObjects:
                satellite = EarthSatellite(lines[0], lines[1], key)
                self.spaceObjects[key] = Satellite(SpaceObjectType.Satellite, key, satellite)

        #Delete satellites no longer in TLE data (except ground stations)
        for key in list(self.spaceObjects.keys()):
            obj = self.spaceObjects[key]
            if obj.type != SpaceObjectType.GroundStation and key not in tle_data:
                del self.spaceObjects[key]

        #Changes boolean for show in space objects
        for name, value in tle_status.items():
            if self.spaceObjects[name].type == SpaceObjectType.GroundStation: continue
            self.spaceObjects[name].show = value
        
        local_now = datetime.now()
        offset_seconds = int((local_now - datetime.utcnow()).total_seconds())
        utc_seconds = self.backend.elapsedSeconds - offset_seconds
        currentTime = local_now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(seconds=utc_seconds)
        for obj in self.spaceObjects.values():
            obj.Update(currentTime)

        positions = []
        keys = []
        for key, obj in self.spaceObjects.items():
            if obj.type == SpaceObjectType.Satellite and obj.show:
                positions.append(obj.position)
                keys.append(key)
                
        self.ObjectAdjacencyMatrix.generate_adjacency_matrix(positions, keys)
