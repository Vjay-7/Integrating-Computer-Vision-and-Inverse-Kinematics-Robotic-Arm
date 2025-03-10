import serial
import time
import csv
import tkinter as tk
from tkinter import ttk

# Configuration
PARK_ANGLES = {
    1: 100,  # Base
    2: 45,   # Shoulder
    3: 0,    # Elbow
    4: 180,  # Wrist pitch
    5: 90,   # Wrist roll
}

# Sequences for different movements
GET_SEQUENCE = [1, 2, 3, 4, 5]  # Sequence for getting an item
SET_SEQUENCE = [1, 2, 4, 3, 5]  # Sequence for setting an item
PARK_SEQUENCE = [1, 2, 4, 3, 5] # Sequence for parking position

# Class coordinates from CSV
CLASS_COORDINATES = {
    'Biodegradable': (100, 100, 90, 90, 90, 90, 90, 90),
    'Non-Biodegradable': (200, 200, 91, 91, 91, 91, 91, 91),
    'Recyclable': (300, 300, 92, 92, 92, 92, 92, 92)
}

class RoboticArmController:
    def __init__(self, port='COM6', baudrate=9600):
        self.servo_speed = 25
        self.interpolation_delay = 5
        self.ser = self.connect_serial(port, baudrate)
        if not self.ser:
            raise Exception("Failed to connect to serial port")
        
        # Initialize settings
        self.set_servo_speed(self.servo_speed)
        self.set_interpolation_delay(self.interpolation_delay)
        
    def connect_serial(self, port, baudrate):
        try:
            ser = serial.Serial(port, baudrate, timeout=1)
            print(f"Connected to {port}")
            return ser
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            return None

    def send_command(self, servo, angle):
        command = f"{servo} {angle}\n"
        self.ser.write(command.encode())
        response = self.ser.readline().decode().strip()
        print(f"Sent: {command.strip()} | Response: {response}")
        time.sleep(0.1)

    def set_servo_speed(self, speed):
        command = f"s {speed}\n"
        self.ser.write(command.encode())
        response = self.ser.readline().decode().strip()
        print(f"Set speed: {speed} | Response: {response}")

    def set_interpolation_delay(self, delay):
        command = f"i {delay}\n"
        self.ser.write(command.encode())
        response = self.ser.readline().decode().strip()
        print(f"Set interpolation delay: {delay} | Response: {response}")

    def release_gripper(self):
        self.send_command(6, -1)
        time.sleep(1)  # Wait for gripper to fully open

    def close_gripper(self):
        self.send_command(6, -2)
        time.sleep(1)  # Wait for gripper to fully close

    def move_to_position(self, coordinates, sequence):
        """Move the arm to specified coordinates using provided sequence"""
        angles = {i: int(angle) for i, angle in enumerate(coordinates[2:7], start=1)}
        
        print(f"Moving using sequence: {sequence}")
        for servo in sequence:
            if servo in angles:
                self.send_command(servo, angles[servo])
                time.sleep(0.5)

    def move_to_park(self):
        """Move arm to parking position using PARK_SEQUENCE"""
        print("Moving to park position using PARK_SEQUENCE...")
        for servo in PARK_SEQUENCE:
            if servo in PARK_ANGLES:
                self.send_command(servo, PARK_ANGLES[servo])
                time.sleep(0.5)
        self.close_gripper()

    def sort_item(self, x, y, item_class):
        """Execute full sorting sequence"""
        try:
            # Start from park position with closed gripper
            self.move_to_park()
            time.sleep(1)

            # Move to pickup position using GET_SEQUENCE
            print(f"Moving to pickup position ({x}, {y})")
            coordinates = self.find_coordinates(x, y)
            if coordinates:
                self.move_to_position(coordinates, GET_SEQUENCE)
                time.sleep(1)
                
                # Pickup sequence
                self.release_gripper()
                time.sleep(1)
                self.close_gripper()
                time.sleep(1)

                # Move to destination based on class using SET_SEQUENCE
                print(f"Moving to {item_class} destination")
                class_coords = CLASS_COORDINATES[item_class]
                self.move_to_position(class_coords, SET_SEQUENCE)
                time.sleep(1)

                # Release item
                self.release_gripper()
                time.sleep(1)

                # Return to park position using PARK_SEQUENCE
                self.move_to_park()
                print("Sorting sequence completed")
            else:
                print("Coordinates not found in mapping file")

        except Exception as e:
            print(f"Error during sorting sequence: {e}")
            self.move_to_park()  # Safety return to park position

    def find_coordinates(self, x, y):
        """Find servo angles for given coordinates from CSV file"""
        try:
            with open('save_angles.csv', 'r') as file:
                reader = csv.reader(file)
                for row in reader:
                    if row and abs(float(row[0]) - x) < 0.01 and abs(float(row[1]) - y) < 0.01:
                        return [float(val) for val in row]
            return None
        except Exception as e:
            print(f"Error reading coordinates: {e}")
            return None

class SortingGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Robotic Arm Sorting System")
        self.controller = RoboticArmController()
        self.create_gui()

    def create_gui(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Coordinate inputs
        ttk.Label(main_frame, text="X Coordinate:").grid(row=0, column=0, padx=5, pady=5)
        self.x_entry = ttk.Entry(main_frame, width=10)
        self.x_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(main_frame, text="Y Coordinate:").grid(row=1, column=0, padx=5, pady=5)
        self.y_entry = ttk.Entry(main_frame, width=10)
        self.y_entry.grid(row=1, column=1, padx=5, pady=5)

        # Class selection
        ttk.Label(main_frame, text="Item Class:").grid(row=2, column=0, padx=5, pady=5)
        self.class_var = tk.StringVar()
        class_combo = ttk.Combobox(main_frame, textvariable=self.class_var)
        class_combo['values'] = ('Biodegradable', 'Non-Biodegradable', 'Recyclable')
        class_combo.grid(row=2, column=1, padx=5, pady=5)
        class_combo.set('Biodegradable')

        # Sort button
        ttk.Button(main_frame, text="Sort Item", 
                  command=self.execute_sort).grid(row=3, column=0, columnspan=2, pady=20)

        # Park button
        ttk.Button(main_frame, text="Park Arm", 
                  command=self.controller.move_to_park).grid(row=4, column=0, columnspan=2, pady=5)

    def execute_sort(self):
        try:
            x = float(self.x_entry.get())
            y = float(self.y_entry.get())
            item_class = self.class_var.get()
            
            self.controller.sort_item(x, y, item_class)
        except ValueError:
            print("Please enter valid coordinates")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SortingGUI()
    app.run()