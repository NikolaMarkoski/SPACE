"""
Filename: sat_sim_output.py
Author: Md Nahid Tanjum

This module manages the output processes for the Satellite Simulator, including writing data
to text and CSV files.
"""

import numpy as np
import csv
import os
from dataclasses import dataclass
from typing import List, Any
from datetime import datetime

@dataclass
class SatSimResult:
    matrices: Any
    satellite_names: List[str]

class SatSimOutput:
    #Handles writing simulation data to text and CSV files.
    def __init__(self):
        #Initializes the SatSimOutput with default attributes.
        self.fl_input = None
        self.matrices = None
        self.timestamps = None
        self.output_file_type = 'csv'
        # Get the directory of the current script (sat_sim_output.py)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Set output_path to 'sat_sim_output' folder within the 'sat_sim' directory
        self.output_path = os.path.join(script_dir, 'output')
        self.keys = None

    def set_output_file_type(self, file_type):
        self.output_file_type = file_type

    def set_output_path(self, output_path):
        self.output_path = output_path

    def set_tle_keys(self, keys):
        self.keys = keys

    def save_matrices(self, matrices):
        self.matrices = matrices
        # Generate timestamp string
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Generate unique output file name with 'sat_sim_output' and date/time
        output_file_name = f"sat_sim_{timestamp_str}.{self.output_file_type}"
        # Construct full output file path
        output_file = os.path.join(self.output_path, output_file_name)
        print(f"Writing output to {output_file}")

        if not self.keys or len(self.keys) == 0:
            if matrices and len(matrices) > 0:
                sample_matrix = matrices[0][1]
                if sample_matrix.ndim > 1:
                    num_satellites = sample_matrix.shape[1]
                else:
                    num_satellites = 1
                self.keys = [f'Satellite {i+1}' for i in range(num_satellites)]

        if matrices:
            if self.output_file_type == "txt":
                self.write_to_file(output_file, matrices, keys=self.keys)
            elif self.output_file_type == "csv":
                self.timestamps = [timestamp for timestamp, _ in matrices]
                self.write_to_csv(output_file, matrices, self.timestamps, keys=self.keys)
            else:
                print(f"Unsupported output file type: {self.output_file_type}")
        else:
            print("No data to write to output file.")

    def write_to_file(self, file, matrices, keys=None):
        #Write data to a text file with headers.
        self.matrices = matrices
        try:
            if not matrices:
                print(f"No data to write to {file}.")
                return False

            # Open the file in write mode to overwrite existing content
            with open(file, "w+") as f:
                if keys and len(keys) > 0:
                    num_satellites = len(keys)
                    f.write(f"Number of satellites: {num_satellites}\n")
                    sat_labels = ', '.join(keys)
                    f.write(f"{sat_labels}\n\n")
                    print(f"Written header with {num_satellites} satellites to {file}.")
                else:
                    if matrices and len(matrices[0][1].shape) > 1:
                        num_satellites = matrices[0][1].shape[1]
                        f.write(f"Number of satellites: {num_satellites}\n")
                        sat_labels = ', '.join([f'Satellite {i+1}' for i in range(num_satellites)])
                        f.write(f"{sat_labels}\n\n")
                        print(f"Written header with {num_satellites} satellites to {file}.")
                    else:
                        print("Cannot determine the number of satellites.")
                        return False

                for timestamp, matrix in matrices:
                    if matrix.size == 0:
                        print(f"Skipping empty matrix at {timestamp}")
                        continue
                    f.write(f"Time: {timestamp}\n")
                    np.savetxt(f, matrix, fmt='%d')
                    f.write("\n")
                    print(f"Written matrix for time {timestamp} to {file}.")
            return True
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False

    def write_to_csv(self, csv_file, matrices, timestamps, keys=None):
        #Write data to a CSV file with headers.
        self.matrices = matrices
        self.timestamps = timestamps
        try:
            if not matrices or not timestamps:
                print(f"No data to write to {csv_file}.")
                return False

            # Determine maximum number of satellites
            max_size = max((matrix.shape[1] for _, matrix in matrices if matrix.size > 0), default=0)

            if max_size == 0:
                print(f"No valid matrix data to write to CSV {csv_file}.")
                return False

            with open(csv_file, mode='w', newline='') as f:
                writer = csv.writer(f)

                # Write number of satellites
                writer.writerow(['Number of satellites:', max_size])
                # Write satellite labels
                if keys and len(keys) == max_size:
                    sat_labels = keys
                else:
                    sat_labels = [f'Satellite {i+1}' for i in range(max_size)]
                writer.writerow(sat_labels)
                # Write header for matrix data
                writer.writerow(['Time'])
                # Write each matrix with timestamp
                for (timestamp, matrix) in matrices:
                    if matrix.size == 0:
                        print(f"Skipping empty matrix at {timestamp}")
                        continue

                    writer.writerow([timestamp])
                    for row in matrix:
                        writer.writerow(row.tolist())
                    writer.writerow([])

            return True
        except Exception as e:
            print(f"Error writing to CSV: {e}")
            return False

    def set_result(self, matrices):
        # Sets the simulation results.
        self.matrices = matrices

    def set_fl_input(self, fl_input):
        #Sets the Federated Learning input.
        self.fl_input = fl_input

    def get_result(self):
        # Retrieves the simulation results as a data class instance.
        if not self.keys or len(self.keys) == 0:
            # Auto-generate satellite names
            if self.matrices and len(self.matrices) > 0:
                sample_matrix = self.matrices[0][1]
                if sample_matrix.ndim > 1:
                    num_satellites = sample_matrix.shape[1]
                else:
                    num_satellites = 1  # In case of 1D matrices
                self.keys = [f'Satellite {i+1}' for i in range(num_satellites)]
            else:
                self.keys = []
        return SatSimResult(
            matrices=self.matrices,
            satellite_names=self.keys,
        )