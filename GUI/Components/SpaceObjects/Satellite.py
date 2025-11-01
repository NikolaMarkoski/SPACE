"""
Filename: Satellite.py
Author: Nikola Markoski, Kartik Punna
Description: This file contains the functions that relate to drawing the satellites and their orbits, updating their positions, and drawing their hover
"""
import numpy as np

from .base import SpaceObject

from OpenGL.GL import *
from OpenGL.GLU import *

from skyfield.api import load

from skyfield.constants import ERAD
from datetime import datetime, timezone, timedelta

orbitResolution = 180

class Satellite(SpaceObject):
    #A class to hold all information relating to a satellite to not overcrowd a dictionary
    def __init__(self, type, name, satellite, ts):
        super().__init__(type, name)
        self.satellite = satellite
        self.position = (0,0,0)
        self.positions = self.PopulateSatellitePositions(ts)

        self.showOrbit = True
        self.color = self.Color()
        self.sphereRadius = 0.03

    def Color(self):
        from random import random
        randomness = random()/1.5
        return (0.5+randomness,0.5+randomness,0.5+randomness)

    def Draw(self, quadric):
        self.DrawSatellite(quadric)
        self.DrawOrbit()
        self.Hover(quadric)

    def Update(self, time=None, ts=None):
        #assuming time is a datetime
        if not ts: ts = load.timescale()
        now = time if time else datetime.now(timezone.utc)
        currentTime = ts.utc(now.year, now.month, now.day, now.hour, now.minute, now.second)

        geocentric = self.satellite.at(currentTime)
        position = geocentric.position.km/(ERAD/1000)

        self.position = position.copy()

    def PopulateSatellitePositions(self, ts):
        revolutionsPerDay = self.satellite.model.no_kozai * 229.1831  # MinutesInADay/2Pi
        orbitalPeriod_days = 1.0 / revolutionsPerDay  # orbital period in days

        if not ts: ts = load.timescale()
        now_dt = datetime.now(timezone.utc)

        # generate times as datetime objects
        deltas = np.linspace(0.0, orbitalPeriod_days, num=orbitResolution, endpoint=False)
        datetimes = [now_dt + timedelta(days=float(d)) for d in deltas]
        times = ts.utc(datetimes)

        # get geocentric positions
        geocentric = self.satellite.at(times)
        positions_km = geocentric.position.km / (ERAD / 1000)  # normalize
        positions = np.stack(positions_km, axis=1)

        return positions

    def DrawSatellite(self, quadric):
        if not self.show: return
        x,y,z = self.position
        glColor3f(*self.color)
        glPushMatrix()
        glTranslate(x,y,z)
        gluSphere(quadric, self.sphereRadius, 40, 40)
        glPopMatrix()

    def DrawOrbit(self):
        if not self.show: return
        if not self.showOrbit: return
        glColor3f(*self.color)
        glLineWidth(2)
        glBegin(GL_LINE_LOOP)
        for x,y,z in self.positions:
            glVertex3f(x,y,z)
        glEnd()

    def Hover(self, quadric):
        if not self.show or not self.hover: return
        x,y,z=self.position
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(*[c + 0.1 for c in self.color],0.2)
        glPushMatrix()
        glTranslate(x,y,z)
        gluSphere(quadric, self.sphereRadius+0.02,40,40)
        glPopMatrix()
        glDisable(GL_BLEND)




