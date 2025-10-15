"""
Filename: sat_sim_gui.py
Author: Nahid Tanjum
Description: This module provides a GUI for the Satellite Simulator using PyQt5.
             It visualizes satellite positions using VTK, displays adjacency matrices using matplotlib,
             and shows network graphs using networkx.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_pdf import PdfPages
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QCheckBox, QWidget, QLabel, QLineEdit, QMessageBox, QFileDialog, QSlider, QSizePolicy, QHBoxLayout, QFrame, QGraphicsOpacityEffect, QScrollArea
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect, QPropertyAnimation, QEasingCurve, QSize

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import vtk

import networkx as nx
from datetime import datetime, timedelta, timezone
from skyfield.api import load

class DropLabel(QLabel):
    fileDropped = pyqtSignal(str)  # Emits TLE content string
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setText("Drop\nHere")
        self.setFixedSize(100, 100)
        self.setStyleSheet("""
            border: 2px dashed #888;
            border-radius: 6px;
            background-color: #f8f8f8;
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet("""
                QLabel {
                    border: 2px dashed #00aaff;
                    background-color: #e0f7ff;
                    padding: 20px;
                    font-size: 14px;
                }
            """)
        else:
            event.ignore()

    def dropEvent(self, event):
        self.resetStyle()
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(".txt") or file_path.endswith(".tle"):
                with open(file_path, "r") as file:
                    self.fileDropped.emit(file_path)
                break

    def dragLeaveEvent(self, event):
        self.resetStyle()

    def resetStyle(self):
        self.setStyleSheet("""
            border: 2px dashed #888;
            border-radius: 6px;
            background-color: #f8f8f8;
        """)

class CollapsibleOverlay(QFrame):
    resizeSignal = pyqtSignal(int)  # Emits new height

    def __init__(self, parent=None):
        
        self.full_height = 150  # Total height when expanded
        self.collapsed_height = 20

        super().__init__(parent)
        self.setStyleSheet("background-color: #f0f0f0; border: 1px solid gray;")
        self.setParent(parent)
        self.setGeometry(0, 0, parent.width(), self.collapsed_height)  # Start with just the button height
        self.setVisible(True)

        self.content_widget = QWidget(self)
        self.content_widget.setGeometry(0, self.collapsed_height, parent.width(), self.full_height - self.collapsed_height)
        self.content_widget.setStyleSheet("background-color: #dddddd;")
        self.content_widget.setVisible(False)

        # Use a horizontal layout
        self.content_layout = QHBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(15)

        # Add DropLabel on the left
        self.drop_label = DropLabel(self)
        self.content_layout.addWidget(self.drop_label)

        # Add your existing content on the right
        self.right_content = QLabel("Collapsible content goes here.")
        self.right_content.setWordWrap(True)
        self.content_layout.addWidget(self.right_content)
        
        self.toggle_button = QPushButton("▼ Expand", self)
        self.toggle_button.setGeometry(0, 0, parent.width(), self.collapsed_height)
        self.toggle_button.clicked.connect(self.toggle)

        # Add opacity effect
        self.opacity_effect = QGraphicsOpacityEffect(self.toggle_button)
        self.toggle_button.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        # Set up enter/leave events
        self.toggle_button.installEventFilter(self)

        #AddAnimation when opening or closing widget
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.expanded = False
        
    def toggle(self):
        self.expanded = not self.expanded
        start_rect = self.geometry()
        end_height = self.full_height if self.expanded else self.collapsed_height
        end_rect = QRect(0, 0, self.parent().width(), end_height)

        self.toggle_button.setText("▲ Collapse" if self.expanded else "▼ Expand")

        self.resizeSignal.emit(end_height)

        if self.expanded:
            self.content_widget.setVisible(True)

        self.animation.stop()
        self.animation.setStartValue(start_rect)
        self.animation.setEndValue(end_rect)
        self.animation.start()        

        if not self.expanded:
            self.animation.finished.connect(self.hide_content)
        else:
            # Disconnect previous connection to avoid multiple calls
            try:
                self.animation.finished.disconnect(self.hide_content)
            except TypeError:
                pass

        if self.expanded:
            self.set_button_opacity(1.0)
        else:
            self.set_button_opacity(0.5)

    def hide_content(self):
        self.content_widget.setVisible(False)

    def set_button_opacity(self, opacity):
        self.opacity_effect.setOpacity(opacity)

    def update_size(self):
        new_width = self.parent().width()
        new_height = self.height()
        self.setGeometry(0, 0, new_width, new_height)
        self.toggle_button.setGeometry(0, 0, new_width, 20)
        self.content_widget.setGeometry(0, 20, new_width, self.full_height - self.collapsed_height)

    def eventFilter(self, source, event):
        if source == self.toggle_button:
            if event.type() == event.Enter:
                self.set_button_opacity(1.0)
            elif event.type() == event.Leave and not self.expanded:
                self.set_button_opacity(0.5)
        return super().eventFilter(source, event)

#------------------------------------------------------------------------------------------------------------------------------

class TLEDisplay(QFrame):
    def __init__(self, parent=None):
        self.full_width = 300  # Total width when expanded
        self.collapsed_width = 20
        self.control_panel_height_reduction = 92 #TODO: find a better way to access this infomration
        self.expanded = True

        self.overlay = parent.overlay
        self.parent = parent
        super().__init__(parent)
        self.setStyleSheet("background-color: #f0f0f0; border: 1px solid gray;")
        self.setParent(parent)
        self.setVisible(True)

        self.set_up_content_window()
        self.set_up_collapse_Button()

        self.set_up_scroll_box()
        
        self.toggle_height(self.overlay.height())
        self.overlay.resizeSignal.connect(self.toggle_height)

    def set_up_collapse_Button(self):
        self.toggle_button = QPushButton("▼ Expand", self)
        self.toggle_button.setGeometry(0, 0, 20, self.height())

        self.opacity_effect = QGraphicsOpacityEffect(self.toggle_button)
        self.toggle_button.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

        # Set up enter/leave events
        self.toggle_button.installEventFilter(self)

        self.toggle_button.clicked.connect(self.toggle_width)

    def set_up_content_window(self):
        self.content_window = QWidget(self)
        self.content_window.setGeometry(0, 0, self.full_width, self.parent.height() - self.overlay.height() - self.control_panel_height_reduction)
        self.content_window.setStyleSheet("background-color: #dddddd;")
        self.content_window.setVisible(True)

    def set_up_scroll_box(self):
    # Use a vertical layout
        main_layout = QVBoxLayout(self.content_window)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        inner_widget = QWidget()
        self.inner_layout = QVBoxLayout(inner_widget)
        
        scroll_area.setWidget(inner_widget)
        main_layout.addWidget(scroll_area)

    def populate_scroll_items(self, tle_data):
        #clear all existing items
        #TODO: update existing items, then Add/Clear additional items as needed.
        for i in reversed(range(self.inner_layout.count())):
            widget_to_remove = self.inner_layout.itemAt(i).widget()

            self.inner_layout.removeWidget(widget_to_remove)

            widget_to_remove.setParent(None)

        for i in tle_data:
            name = str(i)
            line_1 = tle_data[str(i)][0]
            line_2 = tle_data[str(i)][1]
            print("name: " + str(name) + ", line 1: " + str(line_1) + ", line 2: " + str(line_2))

            self.inner_layout.addWidget(TLESlot(name, line_1, line_2))

    def toggle_width(self):
        self.expanded = not self.expanded

        #start_rect = self.geometry()
        end_width = self.full_width if self.expanded else self.collapsed_width
        #end_rect = QRect(0, 0, self.parent().width(), end_height)
        self.setGeometry(0, 20, end_width, self.height())  # Start with just the button height

        self.content_window.setVisible(self.expanded)
        self.toggle_button.setText("▲ Collapse" if self.expanded else "▼ Expand")
        
    def toggle_height(self, height_offset):
        
        target_height = self.parent.height() - height_offset - self.control_panel_height_reduction

        self.setGeometry(0, height_offset, self.full_width, target_height)  # Start with just the button height
        self.toggle_button.setGeometry(0, 0, 20, target_height)

class TLESlot(QWidget):
    def __init__(self, name, line_1, line_2):
        self.enabled = True

        self.tle_name = name
        self.tle_line_1 = line_1
        self.tle_line_2 = line_2

        super().__init__()
        self.setMinimumHeight(150)

        self.layout = QHBoxLayout(self)
        
        self.set_up_display_layer()

    def set_up_display_layer(self):
        #checkbox
        self.checkbox = QCheckBox("")
        self.checkbox.setToolTip("Enable" if self.enabled else "Disable")

        indicator_size = 15 # Default checkbox indicator size in most styles
        self.checkbox.setFixedSize(QSize(indicator_size, indicator_size))
        
        # Optional: Remove padding/margin (works in many styles)
        self.checkbox.setStyleSheet("QCheckBox::indicator { margin: 0px; }")

        self.checkbox.stateChanged.connect(self.checkbox_changed)

        self.layout.addWidget(self.checkbox)

        #label
        item = QLabel(self.tle_name)
        self.layout.addWidget(item)

        #text
        self.toggle_button = QPushButton("▼" if self.enabled else "▲", self)
        self.toggle_button.setGeometry(0, 0, 20, 20)
        self.toggle_button.clicked.connect(self.toggle)
        self.layout.addWidget(self.toggle_button)

    def checkbox_changed(self, state):
        if state == 2:  # 2 = Checked, 0 = Unchecked, 1 = Partially checked
            self.enabled = True
        else:
            self.enabled = False

        self.checkbox.setToolTip("Enable" if self.enabled else "Disable")

    def toggle(self):
        self.toggle_button = QPushButton("▼" if self.enabled else "▲", self)

#------------------------------------------------------------------------------------------------------------------------------

class SatSimGUI(QMainWindow):
    #The main GUI class for the Satellite Simulator.
    gui_initialized = False

    def __init__(self, sat_sim_instance):
        super().__init__()
        # Prevent multiple instances of the GUI
        if SatSimGUI.gui_initialized:
            return
        
        self.set_up_satellite_simulation(sat_sim_instance)

        self.set_up_main_window()
        
        self.set_up_display_panel()

        self.set_up_dropdown()

        self.set_up_control_panel()

        self.set_up_tle_display()

        self.populate_tle_display()

        # Mark the GUI as initialized
        SatSimGUI.gui_initialized = True

    #region - UI set up
    def set_up_satellite_simulation(self, sat_sim_instance):
        self.simulation = sat_sim_instance
        
        # Convert Skyfield Time objects to datetime if necessary
        self.start_time = self.simulation.start_time.utc_datetime() if hasattr(self.simulation.start_time, 'utc_datetime') else self.simulation.start_time
        self.end_time = self.simulation.end_time.utc_datetime() if hasattr(self.simulation.end_time, 'utc_datetime') else self.simulation.end_time
        self.timestep = self.simulation.timestep

    def set_up_main_window(self):
        self.setWindowTitle('Satellite Visualization Over Time')
        screen_resolution = self.screen().size()
        window_width = min(1200, screen_resolution.width())
        window_height = min(900, screen_resolution.height())
        self.setGeometry(QRect(100, 100, window_width, window_height))

        self.centralWidget = QWidget(self)
        self.setCentralWidget(self.centralWidget)

    def set_up_dropdown(self):
        self.overlay = CollapsibleOverlay(self)
        self.overlay.raise_()  # Ensure it's always on top

        #set up event listener
        self.overlay.drop_label.fileDropped.connect(self.on_file_dropped)

    def set_up_display_panel(self):
        self.main_layout = QVBoxLayout(self.centralWidget)
        self.centralWidget.setLayout(self.main_layout)
        
        self.set_up_visualiser()


    def set_up_visualiser(self):
        self.vtkWidget = QVTKRenderWindowInteractor(self.centralWidget)
        self.vtkWidget.Initialize()
        self.vtkWidget.Start()
        self.vtkWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.renderer = vtk.vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.renderer)
        self.renderer.SetBackground(0.1, 0.2, 0.4)
        self.vtkWidget.setMinimumHeight(400)
        self.main_layout.addWidget(self.vtkWidget, stretch=10)

    def set_up_control_panel(self):
        self.control_panel = QHBoxLayout()

        self.start_time_input = QLineEdit(self.start_time.strftime("%Y-%m-%d %H:%M:%S"))
        self.control_panel.addWidget(self.start_time_input)

        slider_widget = QVBoxLayout()

        self.timeframe_input = QLineEdit(str(self.timestep // timedelta(minutes=1)))
        slider_widget.addWidget(self.timeframe_input)

        self.time_slider = QSlider(Qt.Horizontal)
        self.time_slider.setMinimum(0)
        self.time_slider.setMaximum(int((self.end_time - self.start_time) / self.timestep))
        self.time_slider.valueChanged.connect(self.on_slider_change)
        slider_widget.addWidget(self.time_slider)

        btn_update = QPushButton("Update Orbit")
        btn_update.clicked.connect(self.update_orbit)
        slider_widget.addWidget(btn_update)

        self.control_panel.addLayout(slider_widget)

        self.end_time_input = QLineEdit(self.end_time.strftime("%Y-%m-%d %H:%M:%S"))
        self.control_panel.addWidget(self.end_time_input)
        
        self.main_layout.addLayout(self.control_panel)

    def set_up_tle_display(self):
        self.tle_display = TLEDisplay(self)
        self.tle_display.raise_()


    #endregion

    def populate_tle_display(self):
        self.tle_display.populate_scroll_items(self.simulation.tle_data)

    #region - events
    def on_slider_change(self, value):
        #Handle time slider value changes.
        if self.start_time is not None and self.end_time is not None:
            slider_time = self.start_time + (value * self.simulation.timestep)
            
            positions = self.simulation.get_satellite_positions(slider_time)
            
        self.update_visualization(slider_time)

    def on_file_dropped(self, tle_file_path):
        tle_data = self.read_tle_file(tle_file_path)
        self.simulation.set_tle_data(tle_data)

        positions = self.simulation.get_satellite_positions(self.start_time)

        self.update_visualization(self.start_time)
        self.populate_tle_display()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.overlay.update_size()

    def closeEvent(self, event):
        #Handle the close event to properly stop the worker thread.
        if hasattr(self, 'worker') and self.worker is not None:
            self.worker.stop()
            self.worker.wait()
        event.accept()
    #endregion

    #region - Visualisation
    def update_orbit(self):
        #Update the simulation parameters based on user input.
        try:
            if self.simulation.tle_data is None:
                QMessageBox.warning(self, "TLE Data Missing", "Please load a TLE file first.")
                return

            start_time_str = self.start_time_input.text()
            end_time_str = self.end_time_input.text()
            timestep_str = self.timeframe_input.text()

            if not start_time_str or not end_time_str or not timestep_str:
                QMessageBox.warning(self, "Input Missing", "Please provide start time, end time, and timestep.")
                return
            
            # Parse user input into datetime objects
            ts = load.timescale()
            start_time = ts.utc(datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc))
            end_time = ts.utc(datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc))
            timestep = int(timestep_str)

            self.simulation.set_timestep(timestep)
            self.simulation.set_start_end_times(start_time, end_time)

            self.start_time = start_time.utc_datetime()
            self.end_time = end_time.utc_datetime()

            total_steps = int((self.end_time - self.start_time) / timedelta(minutes=timestep))
            self.time_slider.setMaximum(total_steps)

            positions = self.simulation.get_satellite_positions(self.start_time)

            #self.update_label(positions)
            self.update_visualization(self.start_time)
    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {e}")
    
    def update_visualization(self, time):
        #Update the visualization for a specific time.
        positions = self.simulation.get_satellite_positions(time)
        if not positions:
            QMessageBox.warning(self, "No Positions", "No satellite positions were calculated.")
            return

        self.plot_orbits(positions)
        self.vtkWidget.GetRenderWindow().Render()

        #TODO: reintegrate and update graph code
        #self.update_graphs(positions)

    def plot_orbits(self, positions):
        #Plot the satellite orbits and connections in the VTK renderer.
        self.renderer.RemoveAllViewProps()
        bounds = [float('inf'), float('-inf'),  # x_min, x_max
                  float('inf'), float('-inf'),  # y_min, y_max
                  float('inf'), float('-inf')]
        satellite_count = len(positions)
        sphere_radius = 400

        # Generate adjacency matrix and keys
        adj_matrix, keys = self.simulation.generate_adjacency_matrix(positions)
        sat_positions = {}  # Map satellite names to positions

        for name, pos in positions.items():
            if len(pos) != 3 or any(isinstance(p, (float, int)) is False for p in pos):
                continue
            pos = [float(p) for p in pos]
            sat_positions[name] = pos

            sphereSource = vtk.vtkSphereSource()
            sphereSource.SetCenter(pos[0], pos[1], pos[2])
            sphereSource.SetRadius(sphere_radius)
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(sphereSource.GetOutputPort())
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(1.0, 1.0, 1.0)
            self.renderer.AddActor(actor)

            # Add label to the satellite
            labelText = vtk.vtkVectorText()
            labelText.SetText(str(name))

            labelMapper = vtk.vtkPolyDataMapper()
            labelMapper.SetInputConnection(labelText.GetOutputPort())

            labelActor = vtk.vtkFollower()
            labelActor.SetMapper(labelMapper)
            labelActor.SetScale(500)  # Adjust scale as necessary
            labelActor.SetPosition(pos[0], pos[1], pos[2])
            labelActor.GetProperty().SetColor(1.0, 1.0, 0.0)  # Yellow color
            labelActor.SetCamera(self.renderer.GetActiveCamera())

            self.renderer.AddActor(labelActor)

            # Update bounds to ensure all satellites are visible
            for i in range(3):
                bounds[i*2] = min(bounds[i*2], pos[i])
                bounds[i*2+1] = max(bounds[i*2+1], pos[i])

        # Draw connections between satellites based on adjacency matrix
        if adj_matrix is not None and keys is not None:
            num_sats = len(keys)
            for i in range(num_sats):
                for j in range(i + 1, num_sats):
                    if adj_matrix[i][j]:
                        sat1_name = keys[i]
                        sat2_name = keys[j]
                        pos1 = sat_positions.get(sat1_name)
                        pos2 = sat_positions.get(sat2_name)
                        if pos1 and pos2:
                            # Create a line between pos1 and pos2
                            lineSource = vtk.vtkLineSource()
                            lineSource.SetPoint1(pos1)
                            lineSource.SetPoint2(pos2)
                            lineMapper = vtk.vtkPolyDataMapper()
                            lineMapper.SetInputConnection(lineSource.GetOutputPort())
                            lineActor = vtk.vtkActor()
                            lineActor.SetMapper(lineMapper)
                            lineActor.GetProperty().SetColor(0.0, 1.0, 0.0)  # Green color
                            lineActor.GetProperty().SetLineWidth(2)
                            self.renderer.AddActor(lineActor)

        # Calculate the center and range for camera positioning
        x_center = (bounds[0] + bounds[1]) / 2
        y_center = (bounds[2] + bounds[3]) / 2
        z_center = (bounds[4] + bounds[5]) / 2

        x_range = bounds[1] - bounds[0]
        y_range = bounds[3] - bounds[2]
        z_range = bounds[5] - bounds[4]
        max_range = max(x_range, y_range, z_range)
        if max_range == 0:
            max_range = 1

        # Set up the camera and axes
        buffer_space = max_range * 0.5
        camera_distance_multiplier = 2.0 if satellite_count <= 20 else 5.0
        camera_distance = max_range * camera_distance_multiplier + buffer_space
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(max_range, max_range, max_range)
        axes.AxisLabelsOff()
        self.renderer.AddActor(axes)

        camera = self.renderer.GetActiveCamera()
        camera.SetPosition(
            x_center,
            y_center,
            z_center + camera_distance
        )
        camera.SetFocalPoint(
            x_center,
            y_center,
            z_center
        )
        camera.SetViewUp(0, 1, 0)
        camera.SetClippingRange(0.1, camera_distance + max_range * 2)
        self.renderer.ResetCameraClippingRange()
        self.renderer.ResetCamera()
        self.vtkWidget.GetRenderWindow().Render()
    #endregion

    #yoinked from sat_sim_handler.
    #TODO: figure out how to reference the method in the sat_sim_handler, to reduce duplicated code.
    def read_tle_file(self, file_path):
        # Reads TLE data from the specified file path.
        tle_data = {}
        try:
            with open(file_path, 'r') as f:
                lines = [line.strip() for line in f.readlines()]

            # Handle files with or without a title line (3LE or 2LE)
            i = 0
            while i < len(lines):
                if lines[i].startswith('1') or lines[i].startswith('2'):
                    # This is the 2LE format (no title line)
                    tle_line1 = lines[i].strip()
                    tle_line2 = lines[i + 1].strip()
                    tle_data[f"Satellite_{i // 2 + 1}"] = [tle_line1, tle_line2]
                    i += 2
                else:
                    # 3LE format (title line included)
                    name = lines[i].strip()
                    tle_line1 = lines[i + 1].strip()
                    tle_line2 = lines[i + 2].strip()
                    tle_data[name] = [tle_line1, tle_line2]
                    i += 3

            if not tle_data:
                return None
            return tle_data
        
        except OSError:
            raise
        except Exception as e:
            print(f"Error reading TLE file at {file_path}: {e}")
            raise ValueError("Error reading TLE file.")