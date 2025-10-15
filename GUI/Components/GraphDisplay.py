from PyQt5.QtWidgets import QGraphicsOpacityEffect, QSizePolicy, QPushButton, QVBoxLayout, QWidget, QMessageBox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
import networkx as nx

from Components.CollapsibleOverlay import CollapsibleOverlay, OverlaySide

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

    def update_graphs(self):
        adj_matrix = self.backend.adjacencyMatrix
        keys = self.backend.adjacencyMatrixKeys

        if adj_matrix is None: return
        if self.oldMatrix is not None and np.array_equal(self.oldMatrix, adj_matrix): return
        try:
            # --- update adjacency graph ---
            if self.adj_img is None:
                self.adj_img = self.ax_adj.imshow(adj_matrix, cmap='Blues', interpolation='none', aspect='equal')
                self.ax_adj.set_title('Adjacency Matrix')
            else:
                self.adj_img.set_data(adj_matrix)

            if len(self.ax_adj.get_xticks()) != len(keys):
                self.ax_adj.set_xticks(np.arange(len(keys)))
                self.ax_adj.set_yticks(np.arange(len(keys)))
                self.ax_adj.set_xticklabels(keys, rotation=90)
                self.ax_adj.set_yticklabels(keys)

            if self.canvas_adj.width() > 0 and self.canvas_adj.height() > 0:#Get rid of runtimeWarning
                self.canvas_adj.draw()  

            # --- update connection graph ---
            if self.conGraph is None:
                self.conGraph = nx.from_numpy_array(adj_matrix)
                self.conGraphPos = nx.spring_layout(self.conGraph)
                self.conGraphNodes = nx.draw_networkx_nodes(self.conGraph, self.conGraphPos, ax=self.ax_conn, node_color='skyblue')
                self.conGraphEdges = nx.draw_networkx_edges(self.conGraph, self.conGraphPos, ax=self.ax_conn)
                self.conGraphLabels = nx.draw_networkx_labels(self.conGraph, self.conGraphPos, ax=self.ax_conn)
                self.ax_conn.set_title('Connection Graph')
            else:
                self.conGraph = nx.from_numpy_array(adj_matrix)
                if len(self.conGraphPos) != len(self.conGraph):#Will only change graph if nodes are changed, if labels are then it will break
                    if self.conGraphNodes is not None:
                        self.conGraphNodes.remove()
                    if self.conGraphLabels is not None:
                        for label in self.conGraphLabels.values():
                            label.remove()
                    self.conGraphPos = nx.spring_layout(self.conGraph, pos=self.conGraphPos, iterations=1)
                    self.conGraphNodes = nx.draw_networkx_nodes(self.conGraph, self.conGraphPos, ax=self.ax_conn, node_color='skyblue')
                    self.conGraphLabels = nx.draw_networkx_labels(self.conGraph, self.conGraphPos, ax=self.ax_conn)

                if self.conGraphEdges is not None:
                    self.conGraphEdges.remove()
                self.conGraphEdges = nx.draw_networkx_edges(self.conGraph, self.conGraphPos, ax=self.ax_conn)

            if self.canvas_conn.width() > 0 and self.canvas_adj.height() > 0:
                self.canvas_conn.draw()

            self.oldMatrix = adj_matrix.copy()

        except ValueError as e:
            QMessageBox.critical(self, "Error", f"An error occurred during graph update: {e}")
        except Exception as e:
            print(f'Exception Occurred: {e.with_traceback}')

#        
#
#        # Controls layout
#        self.controlsLayout = QVBoxLayout()
#        self.graphLayout.addLayout(self.controlsLayout, stretch=2)
#
#        def update_graphs(self, positions):
#        #Update the adjacency matrix and network graph plots.
#        try:
#            adj_matrix, keys = self.simulation.generate_adjacency_matrix(positions)
#            self.axes[0].cla()
#            self.axes[1].cla()
#
#            self.axes[0].imshow(adj_matrix, cmap='Blues', interpolation='none', aspect='equal')
#            self.axes[0].set_title('Adjacency Matrix')
#            self.axes[0].set_xticks(np.arange(len(keys)))
#            self.axes[0].set_yticks(np.arange(len(keys)))
#            self.axes[0].set_xticklabels(keys, rotation=90)
#            self.axes[0].set_yticklabels(keys)
#
#            G = nx.from_numpy_array(adj_matrix)
#            pos = nx.spring_layout(G)
#            nx.draw(G, pos, ax=self.axes[1], with_labels=True, node_color='skyblue')
#            self.axes[1].set_title('Network Graph')
#
#            self.canvas.draw()
#        except ValueError as e:
#            QMessageBox.critical(self, "Error", f"An error occurred during graph update: {e}")
#
#
#       def calculate_distance(self, pos1, pos2):
#               # Calculate the Euclidean distance between two satellite positions.
#               return np.linalg.norm(np.array(pos1) - np.array(pos2))
#       
#           def generate_adjacency_matrix(self, positions, distance_threshold=10000):
#               # Generate an adjacency matrix based on the distances between satellites.
#               keys = list(positions.keys())
#               size = len(keys)
#               adj_matrix = np.zeros((size, size), dtype=int)
#       
#               # Compute distances between all satellite pairs and populate the adjacency matrix
#               for i in range(size):
#                   for j in range(i + 1, size):
#                       dist = self.calculate_distance(positions[keys[i]], positions[keys[j]])
#                       adj_matrix[i, j] = adj_matrix[j, i] = 1 if dist < distance_threshold else 0
#       
#               return adj_matrix, keys
#
#def save_adj_matrix_for_specified_timeframe(self):
#        #Save the adjacency matrices and network graphs to files.
#        try:
#            output_file, _ = QFileDialog.getSaveFileName(self, "Save Adjacency Matrix", "", "Text Files (*.txt);;All Files (*)")
#            pdf_file, _ = QFileDialog.getSaveFileName(self, "Save Network Graphs PDF", "", "PDF Files (*.pdf);;All Files (*)")
#
#            if output_file and pdf_file:
#                matrices = self.simulation.run_with_adj_matrix()
#                if not matrices:
#                    QMessageBox.warning(self, "No Data", "No data was generated to save.")
#                    return
#
#                with open(output_file, 'w') as f:
#                    for timestamp, matrix in matrices:
#                        formatted_timestamp = timestamp if isinstance(timestamp, str) else timestamp.utc_iso()
#                        f.write(f"Time: {formatted_timestamp}\n")
#                        np.savetxt(f, matrix, fmt='%d')
#                        f.write("\n")
#
#                with PdfPages(pdf_file) as pdf:
#                    for timestamp, matrix in matrices:
#                        formatted_timestamp = timestamp if isinstance(timestamp, str) else timestamp.utc_iso()
#                        G = nx.from_numpy_array(matrix)
#                        pos = nx.spring_layout(G)
#                        plt.figure()
#                        nx.draw(G, pos, with_labels=True, node_color='skyblue')
#                        plt.title(f"Network Graph at {formatted_timestamp}")
#                        pdf.savefig()
#                        plt.close()
#
#                QMessageBox.information(self, "Success", "Adjacency matrix and network graphs saved successfully!")
#
#        except Exception as e:
#            QMessageBox.critical(self, "Error", f"An error occurred while saving the matrix: {e}")