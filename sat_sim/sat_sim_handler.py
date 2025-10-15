"""
Filename: sat_sim_handler.py
Author: Md Nahid Tanjum

This module handles the input of TLE data for satellite simulation processes. It ensures that TLE data
is loaded correctly from files or direct inputs and then passed to the simulation module.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from interfaces.handler import Handler
from skyfield.api import load

class SatSimHandler(Handler):
    # Handles the input of TLE data for satellite simulation processes.
    def __init__(self, sat_sim):
        self.sat_sim = sat_sim
        self.data_loaded = False

    def parse_file(self, file):
        # Reads TLE data from a file and sends it to the SatSim module if not already loaded.
        if self.data_loaded:
            print("Data already loaded, skipping.")
            return
        try:
            tle_data = self.read_tle_file(file)
            if tle_data:
                self.send_data(tle_data)
                self.data_loaded = True
            else:
                print(f"No data found in file: {file}")
        except Exception as e:
            print(f"Error reading TLE file: {e}")
            raise

    def parse_data(self, data):
        # Sends parsed TLE data directly to the SatSim module if not already loaded.
        if self.data_loaded:
            print("Data already loaded, skipping.")
            return
        self.send_data(data)
        self.data_loaded = True

    def send_data(self, data):
        # Sends parsed TLE data to the SatSim module.
        print("Sending data to SatSim...")
        if not data:
            print("No data to send.")
            return
        try:
            if self.sat_sim:
                print("Sending data to SatSim...")
                self.sat_sim.set_tle_data(data)
            else:
                print("SatSim instance not initialized.")
        except Exception as e:
            print(f"Error sending data to SatSim: {e}")

    def run_module(self):
        # Executes the SatSim module by calling its run method.
        self.sat_sim.run()

    #We should be using load.tle_file, but whatever
    def read_tle_file(self, file_path):
        # Reads TLE data from the specified file path.
        tle_data = {}
        try:
            with open(file_path, 'rb') as f:
                lines = [line.strip() for line in f.readlines()]

            #Taken from parse_tle_file from iokit from skyfield
            b0 = b1 = b''
            for b2 in lines:
                if (b2.startswith(b'2 ') and len(b2) >= 69 and b1.startswith(b'1 ') and len(b1) >= 69):
                    b0 = b0.rstrip(b' \n\r')
                    if b0.startswith(b'0 '):
                        b0 = b0[2:]
                    name = b0.decode('ascii')
                    
                    line1 = b1.decode('ascii')
                    line2 = b2.decode('ascii')
                    tle_data[name] = [line1, line2]

                    b0 = b1 = b''
                else:
                    b0 = b1
                    b1 = b2

            return tle_data
        except OSError as e:
            raise e
        except Exception as e:
            print(f"Error reading TLE file at {file_path}: {e}")
            raise ValueError("Error reading TLE file.")