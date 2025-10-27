#Set simulation tle_data to whatever is returned from get_data_from_enabled_tle_slots().
#when instancing TLE_Display, connect your update visuals code using tle_display.update_signal.connect('function name here')

#use the following code/function in __init__ to instantiate a copy
#def set_up_tle_display(self):
#        self.tle_display = TLEDisplay(self)
#        self.tle_display.raise_()
#       
#        #Assumes a reference to the sat_sim has been established.
#        self.tle_display.add_elements(self.simulation.tle_data)

#TODO: clean up and attribution pass
#TODO: figure out how to access the SatSimHandler, to access the read_tle_file() function. once figured out, can remove the duplicated function from this code
#TODO:

from Components.CollapsibleOverlay import CollapsibleOverlay, OverlaySide
from Components.DropLabel import DropLabel
from Components.TLESlot import TLESlot

from PyQt5.QtWidgets import  QHBoxLayout, QLabel, QVBoxLayout, QWidget, QScrollArea, QPushButton, QSizePolicy
from PyQt5.QtCore import Qt

class TLEDisplay(CollapsibleOverlay):

    def __init__(self, parent=None, side= OverlaySide.LEFT):
        self.backend = parent.backend

        super().__init__(parent, side)

        self.control_panel_height_reduction = 260
        self.set_up_drop_label()
        self.set_up_scroll_box()

    def set_up_drop_label(self):
        # Main vertical layout for the drop section
        self.drop_section_layout = QVBoxLayout()
        self.drop_section_layout.setContentsMargins(10, 10, 10, 10)
        self.drop_section_layout.setSpacing(10)

        # Horizontal layout for DropLabel + right content
        self.drop_layout = QHBoxLayout()
        self.drop_layout.setSpacing(15)

        # DropLabel on the left
        self.drop_label = DropLabel(self)
        self.drop_layout.addWidget(self.drop_label)

        # Right content label
        self.right_content = QLabel("Collapsible content goes here.")
        self.right_content.setWordWrap(True)
        self.drop_layout.addWidget(self.right_content)

        # Add drop layout to main vertical layout
        self.drop_section_layout.addLayout(self.drop_layout)

        # Add "Delete All" button beneath DropLabel
        self.delete_all_button = QPushButton("Delete All")
        self.delete_all_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.delete_all_button.clicked.connect(self.backend.delete_all)
        self.delete_all_button.clicked.connect(self.populate_scroll_items)
        self.drop_section_layout.addWidget(self.delete_all_button)

        # Add the combined drop section layout to the content layout
        self.content_layout.addLayout(self.drop_section_layout)

        # Setup event listener
        self.drop_label.fileDropped.connect(self.on_file_dropped)
        self.drop_label.setEnabled(self.expanded)
        self.drop_label.setAcceptDrops(self.expanded)
 
    def set_up_scroll_box(self):
        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        scroll_widget = QWidget()
        self.inner_layout = QVBoxLayout(scroll_widget)
        self.scroll_area.setWidget(scroll_widget)

        # Add scroll area to fill remaining space
        self.content_layout.addWidget(self.scroll_area, stretch=1)

    #TODO: change this to an object pool, to reduce the cost of creating 
    def populate_scroll_items(self):
        #clear all existing items
        #TODO: update existing items, then Add/Clear additional items as needed.
        for i in reversed(range(self.inner_layout.count())):
            widget_to_remove = self.inner_layout.itemAt(i).widget()
            
            #self.inner_layout.removeWidget(widget_to_remove)
            widget_to_remove.setParent(None)
            widget_to_remove.deleteLater()

        for key, value in self.backend.tle_dict.items():
            name = str(key)
            line_1 = value[0]
            line_2 = value[1]

            tle_slot = TLESlot(self, name, line_1, line_2)
            tle_slot.checkbox.stateChanged.connect(self.update_all_enabled_status)
            
            self.inner_layout.addWidget(tle_slot)

    def update_all_enabled_status(self):
        return_dict = {}

        for i in range(self.inner_layout.count()):
            slot = self.inner_layout.itemAt(i).widget()
            if(isinstance(slot, TLESlot)):
                return_dict[slot.tle_name] = slot.checkbox.isChecked()

        self.backend.update_all_element_states(return_dict)

    def add_elements(self, tle_data):
        self.backend.add_elements(tle_data)

        self.populate_scroll_items()

    def delete_element(self, element_name):
        self.backend.delete(element_name)

        self.populate_scroll_items()

    def toggle_size(self):
        if self.expanded:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        super().toggle_size()
        self.drop_label.setEnabled(self.expanded)
        self.drop_label.setAcceptDrops(self.expanded)

    def on_file_dropped(self, tle_file_path):
        print("File dropped from: " + tle_file_path)
        tle_data = self.backend.sat_sim_module.handler.read_tle_file(tle_file_path)

        self.add_elements(tle_data)