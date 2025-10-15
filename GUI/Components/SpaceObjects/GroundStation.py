import sys
import numpy as np

from PyQt5.QtWidgets import QApplication, QMainWindow, QOpenGLWidget
from PyQt5.QtCore import pyqtSignal

from OpenGL.GL import *
from OpenGL.GLU import *

from skyfield.constants import ERAD
import math

from .base import SpaceObject

class GroundStation(SpaceObject):
    def __init__(self, type, name, longitude = None, latitude = None):
        super().__init__(type, name)
        self.position = self.getPositionFromCoordinates(longitude, latitude)
        self.sphereRadius = 0.02
        self.color = (0.5,0.5,1)

    def drawCone(self, radius=4, height=0.1, num_slices=40):
        def getRotation():
            dir_x, dir_y, dir_z = self.position
       
            axis_x = -dir_y
            axis_y = dir_x
            axis_z = 0
            angle = math.acos(dir_z) * 180.0 / math.pi  # in degrees

            if angle != 0:
                return angle, axis_x, axis_y,axis_z
            return 0,0,0,0

        glPushMatrix()
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glDepthMask(GL_FALSE)
        
        glTranslate(*self.position)
        glRotatef(*getRotation())
        glBegin(GL_TRIANGLE_FAN)
        glColor4f(*self.color, 0.5)
        glVertex3f(0, 0, 0)

        for i in range(num_slices + 1):
            angle = i * (2.0 * np.pi) / num_slices
            x = radius * np.cos(angle)
            z = radius * np.sin(angle)
            glVertex3f(x, -height, z)

        glEnd()
        glDepthMask(GL_TRUE)
        glDisable(GL_BLEND)
        glPopMatrix()

    def Draw(self, quadric):
        glColor3f(*self.color)
        glPushMatrix()
        glTranslate(*self.position)
        gluSphere(quadric, self.sphereRadius, 40, 40)
        glPopMatrix()

    def getPositionFromCoordinates(self, long, lat):
        #Convert to radians if not in radian
        long = math.radians(long+180)
        lat = math.radians(lat)
        
        R = 1#ERAD/1000
        x = R * math.cos(lat) * math.cos(long)
        y = R * math.cos(lat) * math.sin(long)
        z = R * math.sin(lat)

        return x,y,z
