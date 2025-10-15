import numpy as np

from OpenGL.GL import *
from OpenGL.GLU import *

from Components.SpaceObjects import SpaceObjectType

class AdjacencyMatrix():
    def __init__(self, backend):
        self.backend = backend

    def satellites_in_los(self, satellites, groundStations):
        """
        Compute satellites in line-of-sight (LOS) for each ground station.

        Parameters
        ----------
        satellites : dict
            Keys are satellite IDs, values are satellite objects with `.position` (np.array([x,y,z])).
        groundStations : dict
            Keys are ground station IDs, values are ground station objects with `.position`.

        Returns
        -------
        gs_to_sats : dict
            Dictionary mapping ground station objects to lists of satellite keys in LOS.
            Format: {GS_obj: ["sat1Key", "sat2Key", ...], ...}
        """
        gs_to_sats = {}

        # Extract satellite keys and positions once
        sat_keys = list(satellites.keys())
        sat_positions = np.array([sat.position for sat in satellites.values()], dtype=float)

        for gs_key, gs_obj in groundStations.items():
            gs_pos = np.array(gs_obj.position, dtype=float)
            vec = sat_positions - gs_pos
            up = gs_pos / np.linalg.norm(gs_pos)
            los_mask = np.dot(vec, up) > 0  # True if satellite is above horizon
            visible_sats = [sat_keys[i] for i, visible in enumerate(los_mask) if visible]
            gs_to_sats[gs_obj] = visible_sats

        return gs_to_sats

    def generate_adjacency_matrix(self, positions, keys):
        if not positions: return
        P = np.array(positions)

        # Compute all pairwise differences (P2 - P1)
        D = P[None, :, :] - P[:, None, :]

        # Quadratic coefficients
        a = np.sum(D * D, axis=2)
        b = 2 * np.sum(P[:, None, :] * D, axis=2)
        c = np.sum(P[:, None, :] * P[:, None, :], axis=2) - 1

        # Discriminant
        disc = b**2 - 4 * a * c

        # Build adjacency matrix (1 = visible, 0 = blocked or same)
        adj_matrix = disc < 0
        np.fill_diagonal(adj_matrix, 0)

        self.backend.adjacencyMatrix = adj_matrix.copy()
        self.backend.adjacencyMatrixKeys = keys.copy()

    def DrawConnections(self, objects, bestConnection=None): #colors for djikstra algorithm for finding best connection, should be [firstsatellite, secondsatellite, thirdsatellite,...]
        adj_matrix = self.backend.adjacencyMatrix
        if adj_matrix is None or not np.any(adj_matrix): return
        satellites = {key: value for key, value in objects.items() if (value.type==SpaceObjectType.Satellite and value.show)}
        groundStations = {key: value for key, value in objects.items() if (value.type==SpaceObjectType.GroundStation and value.show)}
        objs = list(satellites)

        #percentage stuff for future, hopefully
        #signalMaximum = np.max(adj_matrix)
        #signalMinimum = np.min(adj_matrix)

        mask = adj_matrix > 0
        rows, cols = np.triu_indices_from(adj_matrix, k=1)  # k=1 skips diagonal
        indexes = [(r, c) for r, c in zip(rows, cols) if mask[r, c]]

        for row, column in indexes:
            if adj_matrix[row][column]:
                firstObject = objects[objs[row]]
                secondObject = objects[objs[column]]

                if not all([firstObject.show, secondObject.show]): continue #if one of the satellites isn't shown, don't draw connection
                    
                if bestConnection is not None and firstObject in bestConnection and firstObject != bestConnection[-1]:
                    glColor3f(0.0,1.0,0.0) #Green
                else: 
                    glColor3f(1.0,0.0,0.0) #Red
                glLineWidth(2)

                #Variable Dashed lines for variable communications strengths
                #1 because I know adjacency matrix has only true or false
                #value = adj_matrix[row][column]
                percentage = 1#(value - signalMinimum) / (signalMaximum - signalMinimum) 
                glEnable(GL_LINE_STIPPLE)
                pattern = 16**(percentage*4)-1 & 0xFFFF
                glLineStipple(1, pattern)
                    
                glBegin(GL_LINE_STRIP)
                glVertex(firstObject.position)
                glVertex(secondObject.position)
                glEnd()
                    
                glDisable(GL_LINE_STIPPLE)

        
        groundStationLineOfSight = self.satellites_in_los(satellites, groundStations)
        for gStat, sats in groundStationLineOfSight.items():
            for sat in sats:
                satellite = satellites[sat]
                if not satellite.show: continue
                glColor3f(1,0,0)
                glLineWidth(2)
                glBegin(GL_LINE_STRIP)
                glVertex(gStat.position)
                glVertex(satellite.position)
                glEnd()