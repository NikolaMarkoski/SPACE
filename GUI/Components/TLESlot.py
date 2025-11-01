"""
Filename: TLESlot.py
Author: Luke Magnuson
Description: This script is used by the user to control and display specific instances of TLE data that the user supplies.
each slot contains:
    - A checkbox to determine if a satellite is displayed
    - A Button to delete the specific instance of TLE data
    - A button to cycle through the slot display states. A slot can be in a collapsed, brief, or detailed state, 
        which determines how much information on the tle data the slot displayed
"""
from PyQt5.QtWidgets import (
    QApplication, QFrame, QPushButton, QCheckBox, QWidget, QLabel,
    QHBoxLayout, QVBoxLayout
)
from PyQt5.QtCore import QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt


class TLESlot(QWidget):
    def __init__(self, tle_display, name, line_1, line_2):
        super().__init__()

        self.enabled = True
        self.delete_me = False
        self.state = 0  # 0 = collapsed, 1 = expanded, 2 = verbose

        self.tle_display = tle_display
        self.tle_name = name
        self.tle_line_1 = line_1
        self.tle_line_2 = line_2

        # Outer vertical layout
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.outer_layout.setSpacing(2)

        # --- Top bar ---
        self.top_bar = QHBoxLayout()
        self.top_bar.setContentsMargins(0, 0, 0, 0)
        self.top_bar.setSpacing(5)

        # Checkbox
        self.checkbox = QCheckBox("")
        self.checkbox.setToolTip("Enable" if self.enabled else "Disable")
        self.checkbox.setChecked(True)
        self.checkbox.stateChanged.connect(self.checkbox_changed)
        self.top_bar.addWidget(self.checkbox)

        # Label
        self.label = QLabel(self.tle_name)
        self.top_bar.addWidget(self.label)

        # Toggle button
        self.toggle_button = QPushButton("▼")
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.clicked.connect(self.cycle_state)
        self.top_bar.addWidget(self.toggle_button)

        # Delete button
        self.delete_button = QPushButton("🗑")
        self.delete_button.setFixedSize(20, 20)
        self.delete_button.clicked.connect(self.delete)
        self.top_bar.addWidget(self.delete_button)

        self.outer_layout.addLayout(self.top_bar)

        # --- Expandable area ---
        self.expand_area = QFrame()
        self.expand_area.setFixedHeight(0)
        self.expand_area.setMaximumHeight(0)
        self.expand_area.setStyleSheet("background-color: #dcdcdc; border: 1px solid #444;")

        self.expand_layout = QVBoxLayout(self.expand_area)
        self.expand_layout.setContentsMargins(5, 5, 5, 5)

        # Expanded text
        self.tle_text = QLabel(f"{self.tle_line_1}\n{self.tle_line_2}")
        self.tle_text.setWordWrap(True)
        self.expand_layout.addWidget(self.tle_text)

        # Verbose text (hidden unless verbose)
        self.verbose_text = QLabel("")
        self.verbose_text.setWordWrap(True)
        self.verbose_text.setVisible(False)
        self.expand_layout.addWidget(self.verbose_text)

        self.outer_layout.addWidget(self.expand_area)

        # Animation for smooth expand/collapse
        self.anim = QPropertyAnimation(self.expand_area, b"maximumHeight")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

        QApplication.instance().installEventFilter(self)

    # -----------------------
    # UI State
    # -----------------------
    def checkbox_changed(self, state):
        self.enabled = (state == Qt.Checked)
        self.checkbox.setToolTip("Enable" if self.enabled else "Disable")

    def delete(self):
        if not self.delete_me:
            self.delete_me = True
            self.delete_button.setStyleSheet("background-color: red;")
        else:
            self.tle_display.delete_element(self.tle_name)

    def cycle_state(self):
        # 0 -> 1 -> 2 -> 0
        self.state = (self.state + 1) % 3
        self.update_state()

    def update_state(self):
        start_height = self.expand_area.maximumHeight()

        if self.state == 0:  # collapsed
            end_height = 0
            self.toggle_button.setText("▼")
            self.verbose_text.setVisible(False)

        elif self.state == 1:  # expanded
            end_height = 150
            self.toggle_button.setText("▲")
            self.verbose_text.setVisible(False)

        else:  # verbose
            end_height = 250
            self.toggle_button.setText("❖")
            self.verbose_text.setVisible(True)
            self.verbose_text.setText(self.format_verbose())

        self.anim.stop()
        self.anim.setStartValue(start_height)
        self.anim.setEndValue(end_height)
        self.anim.start()

    # -----------------------
    # Verbose parser
    # -----------------------
    def format_verbose(self):
        try:
            # Parse from line 2 (orbital parameters)
            inc = float(self.tle_line_2[8:16])
            raan = float(self.tle_line_2[17:25])
            ecc = float("." + self.tle_line_2[26:33].strip())
            argp = float(self.tle_line_2[34:42])
            mean_anom = float(self.tle_line_2[43:51])
            mean_motion = float(self.tle_line_2[52:63])
            rev_number = int(self.tle_line_2[63:68])

            return (
                f"Satellite: {self.tle_name}\n\n"
                f"Inclination: {inc:.3f}°\n"
                f"RAAN: {raan:.3f}°\n"
                f"Eccentricity: {ecc:.7f}\n"
                f"Arg. of Perigee: {argp:.3f}°\n"
                f"Mean Anomaly: {mean_anom:.3f}°\n"
                f"Mean Motion: {mean_motion:.8f} rev/day\n"
                f"Rev Number @ Epoch: {rev_number}\n"
            )
        except Exception as e:
            return f"Verbose parse failed: {e}"

    # -----------------------
    # Event filter
    # -----------------------
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.MouseButtonPress:
            if not self.delete_button.geometry().contains(event.pos()):
                if self.delete_me:
                    self.delete_me = False
                    self.delete_button.setStyleSheet("")
                else:
                    self.delete()
        return super().eventFilter(obj, event)
