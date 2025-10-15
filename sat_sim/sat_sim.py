"""
Filename: sat_sim.py
Author: Nahid Tanjum
Description: This script handles satellite simulations using TLE data and provides functionality 
             for generating adjacency matrices based on satellite positions, with support for 
             both GUI and CLI operations.
"""

from datetime import datetime, timedelta
from skyfield.api import load, EarthSatellite, utc
from skyfield.constants import ERAD
import numpy as np
import os
from .sat_sim_output import SatSimOutput
from PyQt5.QtWidgets import QApplication


class SatSim:
    # SatSim class manages satellite simulation based on TLE data and handles both GUI and CLI modes.
    def __init__(self, start_time=None, end_time=None, timestep=30, output_file_type="csv", gui_enabled=False, tle_data=None, output_to_file=False):
        # Initialize the SatSim instance with optional parameters for start and end times, timestep, output file type, and GUI mode.
        self.tle_data = tle_data if tle_data else None
        self.timestep = timedelta(minutes=timestep)
        self.sf_timescale = load.timescale()
        self.output = SatSimOutput()
        self.start_time = start_time
        self.end_time = end_time
        self.output_file_type = output_file_type if output_file_type in ["csv", "txt"] else "csv"
        self.output_path = ""
        self.gui_enabled = gui_enabled
        self.output_to_file = output_to_file

        if self.start_time is not None and self.end_time is not None:
            if not isinstance(self.start_time, type(self.sf_timescale.utc(0))):
                raise ValueError("Start time and end time must be Skyfield Time objects")
            if self.start_time.tt >= self.end_time.tt:
                raise ValueError("Start time must be before end time")

    def set_gui_enabled(self, enabled):
        # Enable or disable GUI mode.
        self.gui_enabled = enabled

    def set_tle_data(self, tle_data):
        # Set the TLE data used in the simulation.
        self.tle_data = tle_data if tle_data else None

    def set_timestep(self, timestep):
        # Set the simulation timestep (in minutes).
        self.timestep = timedelta(minutes=timestep)

    def set_start_end_times(self, start, end):
        # Set the start and end times for the simulation.
        self.start_time = start
        self.end_time = end

    def set_output_file_type(self, file_type):
        # Set the output file format (csv or txt).
        self.output_file_type = file_type
        self.output.set_output_file_type(file_type)

    def set_output_to_file(self, output_to_file):
        # Set whether to output to file.
        self.output_to_file = output_to_file

    def run_gui(self):
        # Launch the satellite simulation GUI.
        from .sat_sim_gui import SatSimGUI
        import sys
        app = QApplication(sys.argv)
        gui = SatSimGUI(self)
        gui.show()
        sys.exit(app.exec_())

    #I don't think this is needed anymore
    #And if it is, satellite positions should be gotten from spaceObjects
    def get_satellite_positions(self, time):
        # Get satellite positions at a given time.
        if self.tle_data is None or len(self.tle_data) == 0:
            print("No TLE data provided. Cannot calculate satellite positions.")
            return {}
        if isinstance(time, datetime):
            # Convert Python datetime object to Skyfield time object
            time = self.sf_timescale.from_datetime(time)

        positions = {}
        # Calculate satellite positions using TLE data
        for name, tle in self.tle_data.items():
            if len(tle) < 2:
                print(f"Warning: Incomplete TLE data for {name}. Skipping this entry.")
                continue  # Skip the incomplete TLE entry

            try:
                tle_line1, tle_line2 = tle
                satellite = EarthSatellite(tle_line1, tle_line2, name)
                geocentric = satellite.at(time)
                positions[name] = geocentric.position.km
            except Exception as e:
                print(f"Error processing TLE data for {name}: {e}")
                continue  # Skip this satellite if there's an error
        return positions

    #Not needed, because computed in AdjacencyMatrix.py now
    def generate_adjacency_matrix(self, positions):
        if not isinstance(positions, dict) or not positions: return
        keys = list(positions)
        P = np.array(list(positions.values()))

        # Compute all pairwise differences (P2 - P1)
        D = P[None, :, :] - P[:, None, :]

        # Quadratic coefficients
        a = np.sum(D * D, axis=2)
        b = 2 * np.sum(P[:, None, :] * D, axis=2)
        c = np.sum(P[:, None, :] * P[:, None, :], axis=2) - (ERAD/1000)**2

        # Discriminant
        disc = b**2 - 4 * a * c

        # Build adjacency matrix (1 = visible, 0 = blocked or same)
        adj_matrix = disc < 0
        np.fill_diagonal(adj_matrix, 0)

        return adj_matrix, keys

    def run_with_adj_matrix(self):
        # Run the simulation in CLI mode and generate adjacency matrices.
        if not self.tle_data:
            print("No TLE data loaded. Please provide valid TLE data.")
            return []

        current_time = self.start_time
        end_time = self.end_time
        timestep_days = self.timestep.total_seconds() / 86400.0

        matrices = []
        timestamps = []

        # Loop through time increments and generate adjacency matrices
        while current_time.tt < end_time.tt:
            try:
                positions = self.get_satellite_positions(current_time)

                if not positions:
                    print(f"Skipping timestep {current_time.utc_datetime()}: No positions calculated.")
                    current_time = current_time + timestep_days
                    continue

                # Generate adjacency matrix
                adj_matrix, _ = self.generate_adjacency_matrix(positions)
                matrices.append((current_time.utc_datetime().strftime('%Y-%m-%d %H:%M:%S'), adj_matrix))

                # Increment the current_time by the timestep in days
                current_time = current_time + timestep_days

            except Exception as e:
                print(f"Error during simulation at time {current_time.utc_datetime()}: {e}")
                import traceback
                traceback.print_exc()
                break

        # Save results using the output module
        if self.output_to_file and matrices:
            self.output.set_tle_keys(list(self.tle_data.keys()))
            self.output.save_matrices(matrices)
        else:
            print("No data to write to output file.")

        if not matrices:
            print("Warning: No adjacency matrices generated. Check TLE data and timestep settings.")

        # Set results in output module
        self.output.set_result(matrices)

        return matrices

    def run(self):
        # Run the simulation based on the mode (CLI or GUI).
        if self.gui_enabled:
            self.run_gui()  # Run in GUI mode
        else:
            self.run_with_adj_matrix()  # Run in CLI mode