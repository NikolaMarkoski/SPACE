"""
Filename: base.py
Author: Nikola Markoski
Description: A base class for space objects. These currently include ground stations and satellites. If more are needed please use this base class to tie them together.
"""
from enum import Enum

class SpaceObjectType(Enum):
    Globe = "Globe"
    GroundStation = "GroundStation"
    Satellite = "Satellite"

class SpaceObject():
    def __init__(self, type, name):
        self.type = type #Type of SpaceObject
        self.position = None
        self.name = name
        self.show = True
        self.hover = False

    def Draw(self):
        pass

    def Update(self, time=None, ts=None):
        pass