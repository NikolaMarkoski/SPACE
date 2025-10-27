from PyQt5.QtWidgets import QGraphicsOpacityEffect, QSizePolicy, QPushButton, QVBoxLayout, QWidget, QMessageBox, QToolTip
from PyQt5.QtCore import QPoint
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import networkx as nx
import random
import traceback

from Components.CollapsibleOverlay import CollapsibleOverlay, OverlaySide

NODESIZE=200
EDGESIZE=0.5
FONTSIZE=6

class GraphDisplay(CollapsibleOverlay):

    def __init__(self, parent=None, side= OverlaySide.RIGHT):
        self.backend = parent.backend

        super().__init__(parent,side)

        self.control_panel_height_reduction = 260
        self.set_up_adjacency_graph()
        self.set_up_connection_graph()

        self.backend.subscribe(self.update_graphs)

        self.adj_img = None
        self.conGraph = None
        self.conGraphPos = None
        self.conGraphNodes = None
        self.conGraphEdges = None
        self.conGraphLabels = None

        self.oldMatrix = None
        self.oldKeys = []

    def set_up_adjacency_graph(self):
        # Layout for graphs and controls
        self.graphLayout = QVBoxLayout()
        self.content_layout.addLayout(self.graphLayout, stretch=5)

        # --- Adjacency graph ---
        self.figure_adj, self.ax_adj = plt.subplots(figsize=(6, 4))
        self.canvas_adj = FigureCanvas(self.figure_adj)
        self.canvas_adj.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.graphLayout.addWidget(self.canvas_adj, stretch=5)


    def set_up_connection_graph(self):
        # --- Connection graph ---
        self.figure_conn, self.ax_conn = plt.subplots(figsize=(6, 4))
        self.canvas_conn = FigureCanvas(self.figure_conn)
        self.canvas_conn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.graphLayout.addWidget(self.canvas_conn, stretch=5)

    def on_node_hover(self, event):
        if event.inaxes != self.ax_conn:
            return

        if self.conGraphNodes is None:
            return

        # Get positions and check mouse proximity
        for node, (x, y) in self.conGraphPos.items():
            # Convert data coords to pixel coords
            xy_disp = self.ax_conn.transData.transform((x, y))
            dx, dy = xy_disp[0] - event.x, xy_disp[1] - event.y
            dist = (dx**2 + dy**2)**0.5

            if dist < 10:  # adjust sensitivity threshold
                node_name = self.backend.satelliteNames[node]
                
                inv_y = self.canvas_conn.height() - int(event.y)
                QToolTip.showText(
                    self.canvas_conn.mapToGlobal(QPoint(int(event.x), inv_y)),
                    node_name,
                    self.canvas_conn
                )
                return

        QToolTip.hideText()

    def update_graphs(self):
        adj_matrix = self.backend.adjacencyMatrix
        keys = self.backend.adjacencyMatrixKeys
        
        if adj_matrix is None:
            if self.adj_img is not None:
                self.adj_img = None
                self.ax_adj.clear()
                self.canvas_adj.draw()
            if self.conGraph is not None: 
                self.conGraph = None
                self.ax_conn.clear()
                self.canvas_conn.draw()
            return
        if self.oldMatrix is not None and np.array_equal(self.oldMatrix, adj_matrix): return
        try:
            # --- update adjacency graph ---
            self.adj_img = self.ax_adj.imshow(adj_matrix, cmap='Blues', interpolation='none', aspect='equal')
            self.ax_adj.clear()
            self.ax_adj.imshow(adj_matrix, cmap='Blues', interpolation='none', aspect='equal')
            self.ax_adj.set_title('Adjacency Matrix')
            self.ax_adj.set_xticks(np.arange(len(keys)))
            self.ax_adj.set_yticks(np.arange(len(keys)))
            self.ax_adj.set_xticklabels(keys, rotation=90)
            self.ax_adj.set_yticklabels(keys) 

            # --- update connection graph ---
            if self.conGraph is None:
                self.conGraph = nx.from_numpy_array(adj_matrix)
                self.conGraphPos = nx.arf_layout(self.conGraph)
                self.conGraphNodes = nx.draw_networkx_nodes(self.conGraph, self.conGraphPos, ax=self.ax_conn, node_color='skyblue', node_size=NODESIZE)
                self.conGraphEdges = nx.draw_networkx_edges(self.conGraph, self.conGraphPos, ax=self.ax_conn, alpha=0.5, width=EDGESIZE)
                self.conGraphLabels = nx.draw_networkx_labels(self.conGraph, self.conGraphPos, ax=self.ax_conn, font_size=FONTSIZE, labels={i: self.backend.satelliteNames[i][0:3] for i in self.conGraph})
                self.ax_conn.set_title('Connection Graph')
            else:
                self.conGraph = nx.from_numpy_array(adj_matrix)
                if len(self.conGraphPos) != len(self.conGraph):#Will only change graph if nodes are changed, if labels are then it will break
                    if self.conGraphNodes:
                        self.conGraphNodes.remove()
                    if self.conGraphLabels:
                        for label in self.conGraphLabels.values():
                            label.remove()
                    self.conGraphPos = nx.arf_layout(self.conGraph)
                    self.conGraphNodes = nx.draw_networkx_nodes(self.conGraph, self.conGraphPos, ax=self.ax_conn, node_color='skyblue', node_size=NODESIZE)
                self.conGraphLabels = nx.draw_networkx_labels(self.conGraph, self.conGraphPos, ax=self.ax_conn, font_size=FONTSIZE, labels={i: self.backend.satelliteNames[i][0:3] for i in self.conGraph})

                if self.conGraphEdges:
                    self.conGraphEdges.remove()
                self.conGraphEdges = nx.draw_networkx_edges(self.conGraph, self.conGraphPos, ax=self.ax_conn, alpha=0.5, width=EDGESIZE)

            if self.canvas_conn.width() > 0 and self.canvas_adj.height() > 0:
                self.canvas_conn.draw()
                self.canvas_adj.draw()
                self.canvas_conn.mpl_connect('motion_notify_event', self.on_node_hover)

            self.oldMatrix = adj_matrix.copy()

        except ValueError as e:
            QMessageBox.critical(self, "Error", f"An error occurred during graph update: {e}")
        except Exception as e:
            print(f"Exception Occurred: {e}\nTraceback:\n{''.join(traceback.format_exception(e))}")

