"""
Filename: sat_sim_config.py
Author: Md Nahid Tanjum

This module manages the configuration settings for the Satellite Simulator. It reads configuration options
from a JSON file and applies them to the simulation instance, ensuring that all inputs are valid and logical.
"""

import json
from datetime import datetime
from skyfield.api import load, Topos, utc
from interfaces.config import Config

class SatSimConfig:
    def __init__(self, sat_sim=None):
        # Initialize with an optional satellite simulation instance and load the timescale.
        self.ts = load.timescale()
        self.sat_sim = sat_sim
        self.config_loaded = False

    def _convert_to_timestamp(self, time_str):
        # Converts date-time string to a Skyfield time object.
        try:
            dt_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            dt_obj = dt_obj.replace(tzinfo=utc)
            return self.ts.from_datetime(dt_obj)
        except ValueError:
            raise ValueError(f"Invalid datetime format: {time_str}. Correct format should be YYYY-MM-DD HH:MM:SS")

    def set_gui_enabled(self, enabled):
        # Sets the GUI mode based on the boolean flag.
        self.sat_sim.set_gui_enabled(enabled)

    def read_options(self, options):
        # Applies configuration options to the SatSim instance.
        if self.config_loaded:
            return

        # Check for all required fields.
        required_fields = ["gui", "start_time", "end_time", "timestep", "output_file_type"]
        for field in required_fields:
            if field not in options:
                raise ValueError(f"Missing configuration field: {field}")

        # Convert start and end times to timestamps and set them.
        start_time = self._convert_to_timestamp(options['start_time'])
        end_time = self._convert_to_timestamp(options['end_time'])
        if start_time.tt >= end_time.tt:
            raise ValueError("Start time must be before end time.")
        self.sat_sim.set_start_end_times(start=start_time, end=end_time)

        # Set the simulation timestep.
        timestep = options.get('timestep')
        if not isinstance(timestep, int) or timestep < 1:
            raise ValueError(f"Timestep must be an integer greater than 0. Received: {timestep}")
        self.sat_sim.set_timestep(timestep)

        # Set GUI enabled state.
        self.set_gui_enabled(options.get('gui', False))

        # Set the output file type.
        if options['output_file_type'] not in ["csv", "txt"]:
            raise ValueError("Output file type must be 'csv' or 'txt'.")
        self.sat_sim.set_output_file_type(options['output_file_type'])

        # Set output to file.
        if 'module_settings' in options and 'output_to_file' in options['module_settings']:
            self.sat_sim.set_output_to_file(options["module_settings"]["output_to_file"])

        # Configure the ground station if specified.
        if 'ground_station' in options:
            location = options['ground_station'].get('location')
            if not location or 'lat' not in location or 'long' not in location:
                raise ValueError("Ground station location must include 'lat' and 'long'.")
            lat = location['lat']
            long = location['long']
            if not (-90 <= lat <= 90 and -180 <= long <= 180):
                raise ValueError("Latitude must be between -90 and 90, longitude between -180 and 180.")
            self.sat_sim.ground_station = Topos(latitude_degrees=lat, longitude_degrees=long)

        self.config_loaded = True

    def read_options_from_file(self, file_path):
        # Reads and applies configuration options from a specified JSON file.
        if self.config_loaded:
            return

        try:
            with open(file_path, 'r') as file:
                options = json.load(file)
            self.read_options(options)
        except FileNotFoundError:
            print("Configuration file not found.")
        except json.JSONDecodeError:
            print("Error parsing the JSON file.")
        except IOError as e:
            print(f"Unable to read file: {e}")
        except Exception as e:
            print(f"Error reading options from file: {e}")
            self.config_loaded = False