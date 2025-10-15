from PyQt5.QtCore import QEasingCurve, QPropertyAnimation, QEvent, QParallelAnimationGroup
from PyQt5.QtWidgets import QPushButton, QWidget, QFrame, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect
from enum import Enum


class OverlaySide(Enum):
    LEFT = 1
    RIGHT = 2
    TOP = 3
    BOTTOM = 4


class CollapsibleOverlay(QFrame):
    def __init__(self, parent=None, side=OverlaySide.LEFT):
        super().__init__(parent)

        self.side = side
        self.expanded = False

        self.full_size = 450
        self.collapsed_size = 20
        self.above_height_amount = 0
        self.control_panel_height_reduction = 110

        # keep refs for running animations / groups
        self._group = None
        self._anim = None
        self._fade = None

        # Event filter to track parent resize
        if parent is not None:
            parent.installEventFilter(self)

        # Overlay content container
        self.overlay = QWidget(self)
        self.overlay.setStyleSheet("background-color: #dddddd;")

        self.content_layout = QVBoxLayout(self.overlay)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Fade effect: ensure initial opacity matches initial expanded state
        self.opacity_effect = QGraphicsOpacityEffect(self.overlay)
        self.overlay.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0 if self.expanded else 0.0)
        self.overlay.setEnabled(self.expanded)

        # Main layout + toggle button
        if self.side in (OverlaySide.LEFT, OverlaySide.RIGHT):
            self.main_layout = QHBoxLayout(self)
            self.toggle_button = QPushButton("▶" if self.side == OverlaySide.LEFT else "◀")
            self.toggle_button.setFixedWidth(self.collapsed_size)

            if self.side == OverlaySide.LEFT:
                self.main_layout.addWidget(self.toggle_button)
                self.main_layout.addWidget(self.overlay, stretch=1)
            else:
                self.main_layout.addWidget(self.overlay, stretch=1)
                self.main_layout.addWidget(self.toggle_button)

        else:  # TOP or BOTTOM
            self.main_layout = QVBoxLayout(self)
            self.toggle_button = QPushButton("▼" if self.side == OverlaySide.TOP else "▲")
            self.toggle_button.setFixedHeight(self.collapsed_size)

            if self.side == OverlaySide.TOP:
                self.main_layout.addWidget(self.toggle_button)
                self.main_layout.addWidget(self.overlay, stretch=1)
            else:
                self.main_layout.addWidget(self.overlay, stretch=1)
                self.main_layout.addWidget(self.toggle_button)

        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Connect button
        self.toggle_button.clicked.connect(self.toggle_size)
        self.update_size()

    # ----------------------------
    # Helpers
    # ----------------------------
    def _pause_heavy_updates(self, pause: bool):
        """Optional: if you attach a heavy widget (e.g. matplotlib canvas) as self.canvas,
        this will temporarily disable its updates to reduce repaint stutter during animation."""
        canvas = getattr(self, "canvas", None)
        if canvas is not None:
            canvas.setUpdatesEnabled(not pause)

    def _stop_animations(self):
        """Stop & clear any running animations/groups before starting new ones."""
        attributes = ["_group", "_anim", "_fade"]
        for attr in attributes:
            obj = getattr(self, attr, None)
            
            if obj is None: continue

            try: 
                obj.stop()
            except Exception as e:
                print(f'{e}')

            setattr(self, attr, None)

    # ----------------------------
    # Toggle / coordination
    # ----------------------------
    def toggle_size(self):
        # stop any current animations to avoid conflicts
        self._stop_animations()

        # flip state & update icon
        self.expanded = not self.expanded
        self.update_button_icon()

        # When expanding, enable immediately so fade is visible.
        if self.expanded:
            self.overlay.setEnabled(True)

        # optionally pause heavy child updates during animation
        self._pause_heavy_updates(True)

        # Build animations (they do NOT start by themselves)
        size_anim = self.animate_size()
        fade_anim = self.animate_fade()

        # Run them in parallel for a single finished signal
        group = QParallelAnimationGroup(self)
        group.addAnimation(size_anim)
        group.addAnimation(fade_anim)

        def _on_finished():
            # apply final constraints/positioning
            self.update_size()
            # re-enable heavy updates
            self._pause_heavy_updates(False)
            # when collapsed, disable overlay so it doesn't block clicks
            if not self.expanded:
                self.overlay.setEnabled(False)
            # clear ref
            self._group = None

        group.finished.connect(_on_finished)
        self._group = group
        group.start()

    # ----------------------------
    # Button and icons
    # ----------------------------
    def update_button_icon(self):
        if self.side == OverlaySide.LEFT:
            self.toggle_button.setText("◀" if self.expanded else "▶")
        elif self.side == OverlaySide.RIGHT:
            self.toggle_button.setText("▶" if self.expanded else "◀")
        elif self.side == OverlaySide.TOP:
            self.toggle_button.setText("▲" if self.expanded else "▼")
        else:
            self.toggle_button.setText("▼" if self.expanded else "▲")

    # ----------------------------
    # Sizing & positioning
    # ----------------------------
    def update_size(self):
        """Set overlay dimensions based on expansion state and parent size"""
        parent = self.parent()
        if not parent:
            return

        if self.side in (OverlaySide.LEFT, OverlaySide.RIGHT):
            target_width = self.full_size if self.expanded else self.collapsed_size
            target_height = max(50, parent.height() - self.above_height_amount - self.control_panel_height_reduction)

            # lock the controlled dimension, give sensible min/max for the free dimension
            self.setFixedWidth(target_width)
            self.setMinimumHeight(target_height)
            self.setMaximumHeight(target_height)
            self.toggle_button.setFixedHeight(target_height)

        else:  # TOP or BOTTOM
            target_height = self.full_size if self.expanded else self.collapsed_size
            target_width = max(50, parent.width())

            self.setFixedHeight(target_height)
            self.setMinimumWidth(target_width)
            self.setMaximumWidth(target_width)
            self.toggle_button.setFixedWidth(target_width)

        self.reposition()

    def reposition(self):
        """Dock overlay to the correct side of the parent"""
        parent = self.parent()
        if not parent:
            return

        if self.side == OverlaySide.LEFT:
            self.move(0, self.above_height_amount)
        elif self.side == OverlaySide.RIGHT:
            self.move(parent.width() - self.width(), self.above_height_amount)
        elif self.side == OverlaySide.TOP:
            self.move(0, 0)
        elif self.side == OverlaySide.BOTTOM:
            self.move(0, parent.height() - self.height())

    # ----------------------------
    # Animations (create, but don't start)
    # ----------------------------
    def animate_size(self):
        if self.side in (OverlaySide.LEFT, OverlaySide.RIGHT):
            start_width = self.width()
            end_width = self.full_size if self.expanded else self.collapsed_size

            anim = QPropertyAnimation(self, b"maximumWidth", self)
            anim.setDuration(300)
            anim.setStartValue(start_width)
            anim.setEndValue(end_width)
            anim.setEasingCurve(QEasingCurve.InOutCubic)

            # keep a ref so toggles can stop it if needed
            self._anim = anim
            return anim
        else:
            start_height = self.height()
            end_height = self.full_size if self.expanded else self.collapsed_size

            anim = QPropertyAnimation(self, b"maximumHeight", self)
            anim.setDuration(300)
            anim.setStartValue(start_height)
            anim.setEndValue(end_height)
            anim.setEasingCurve(QEasingCurve.InOutCubic)

            self._anim = anim
            return anim

    def animate_fade(self):
        # Use the current opacity as the start so mid-toggle reversals are smooth
        start_opacity = self.opacity_effect.opacity()
        end_opacity = 1.0 if self.expanded else 0.0

        fade = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        fade.setDuration(300)
        fade.setStartValue(start_opacity)
        fade.setEndValue(end_opacity)
        fade.setEasingCurve(QEasingCurve.InOutCubic)

        self._fade = fade
        return fade

    # ----------------------------
    # Event handling
    # ----------------------------
    def eventFilter(self, obj, event):
        """Listen for parent resize events"""
        if obj is self.parent() and event.type() == QEvent.Resize:
            self.update_size()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        """Keep overlay docked when overlay itself resizes"""
        self.reposition()
        super().resizeEvent(event)