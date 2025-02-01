import serial
import tkinter as tk
import time
import csv
import os
import threading

# Attempt to open the serial port
try:
    ser = serial.Serial('COM6', 9600, timeout=1)
except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
    exit()

# Function to send the command to the Arduino
def send_command(servo, angle):
    command = f"{servo} {angle}\n"
    ser.write(command.encode())
    time.sleep(0.1)

def release_gripper():
    # Send -1 to release grip (open to 23 degrees)
    command = "6 -1\n"
    ser.write(command.encode())
    time.sleep(0.1)

def start_gripping():
    # Send -2 to start adaptive gripping
    command = "6 -2\n"
    ser.write(command.encode())
    time.sleep(0.1)

# Position constants
PARK_ANGLES = {
    1: 102,  # Base
    2: 61,   # Shoulder
    3: 51,   # Elbow
    4: 37,   # Wrist pitch
    5: 90,   # Wrist roll
}

DROP_ANGLES = {
    1: 102,  # Base
    2: 61,   # Shoulder
    3: 51,   # Elbow
    4: 155,  # Wrist pitch - modified for dropping
    5: 90,   # Wrist roll
}

def move_servos_sequence(angles_dict):
    sequence = [1,2,3,4,5]#[3, 2, 1, 4, 5]  # Correct movement sequence
    for servo in sequence:
        if servo in angles_dict:
            angle = angles_dict[servo]
            send_command(servo, angle)
            servo_angles[servo - 1] = angle
            if angle_labels[servo - 1]:
                angle_labels[servo - 1].config(text=f"Angle: {angle}")
            if scales[servo - 1]:
                scales[servo - 1].set(angle)
            time.sleep(0.5)  # Allow time for servo movement

def execute_get_sequence():
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        
        # Step 1: Move to target coordinates (skip park position and opening gripper)
        print("Moving to target position...")
        target_found = False
        target_angles = {}
        
        with open('save_angles.csv', mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    saved_x = float(row[0])
                    saved_y = float(row[1])
                    if abs(saved_x - x) < 0.01 and abs(saved_y - y) < 0.01:  # Using small threshold for float comparison
                        angles = list(map(int, row[2:7]))  # Get only servo angles 1-5
                        for i, angle in enumerate(angles, 1):
                            target_angles[i] = angle
                        target_found = True
                        break
        
        if not target_found:
            print("Coordinates not found in saved positions!")
            return
            
        move_servos_sequence(target_angles)
        time.sleep(1)
        
        # Step 2: Grip the item
        print("Gripping item...")
        start_gripping()
        time.sleep(1.5)  # Give more time for gripping
        
        # Step 3: Move to drop position
        print("Moving to drop position...")
        move_servos_sequence(DROP_ANGLES)
        time.sleep(1)  # Wait at drop position
        
        # Step 4: Return to park position
        print("Returning to park position...")
        move_servos_sequence(PARK_ANGLES)
        
        print("Sequence complete!")
        
    except ValueError as e:
        print(f"Error with coordinates: {e}")
    except IOError as e:
        print(f"Error reading coordinates file: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def get_item():
    # Run the sequence in a separate thread to keep GUI responsive
    thread = threading.Thread(target=execute_get_sequence)
    thread.daemon = True  # Thread will close with main program
    thread.start()

def create_gripper_controls(frame):
    grip_frame = tk.Frame(frame)
    grip_frame.pack(side=tk.TOP, pady=5)
    
    open_button = tk.Button(grip_frame, text="Release", command=release_gripper)
    open_button.pack(side=tk.LEFT, padx=5)
    
    grip_button = tk.Button(grip_frame, text="Grip", command=start_gripping)
    grip_button.pack(side=tk.LEFT, padx=5)
    
    get_button = tk.Button(grip_frame, text="Get Item", command=get_item)
    get_button.pack(side=tk.LEFT, padx=5)

# Modified park_servos function
def park_servos():
    move_servos_sequence(PARK_ANGLES)

# Create servo controls
def create_servo_controls(servo_number):
    frame = tk.Frame(root)
    frame.pack(side=tk.LEFT, padx=10, pady=5)

    label = tk.Label(frame, text=f"Servo {servo_number}")
    label.pack(side=tk.TOP)

    if servo_number == 6:
        create_gripper_controls(frame)
        return None, None
    else:
        if servo_number == 1:
            scale = tk.Scale(frame, from_=0, to=180, orient=tk.HORIZONTAL,
                           length=200, command=lambda val, sn=servo_number: adjust_servo(sn, val))
        elif servo_number == 2:
            scale = tk.Scale(frame, from_=61, to=120, orient=tk.VERTICAL,
                           length=200, command=lambda val, sn=servo_number: adjust_servo(sn, val))
        elif servo_number == 3:
            scale = tk.Scale(frame, from_=100, to=0, orient=tk.VERTICAL,
                           length=200, command=lambda val, sn=servo_number: adjust_servo(sn, val))
        elif servo_number == 4:
            scale = tk.Scale(frame, from_=180, to=0, orient=tk.VERTICAL,
                           length=200, command=lambda val, sn=servo_number: adjust_servo(sn, val))
        else:  # servo 5
            scale = tk.Scale(frame, from_=0, to=180, orient=tk.HORIZONTAL,
                           length=200, command=lambda val, sn=servo_number: adjust_servo(sn, val))

        scale.set(servo_angles[servo_number - 1])
        scale.pack(side=tk.TOP)

        angle_label = tk.Label(frame, text=f"Angle: {servo_angles[servo_number - 1]}")
        angle_label.pack(side=tk.TOP)

        entry = tk.Entry(frame, width=5)
        entry.pack(side=tk.TOP, pady=5)
        
        button = tk.Button(frame, text="Set Angle", 
                          command=lambda sn=servo_number, ent=entry: set_servo_angle(sn, ent))
        button.pack(side=tk.TOP)

        return scale, angle_label

def adjust_servo(servo_number, angle):
    global servo_angles, angle_labels
    new_angle = int(float(angle))
    servo_angles[servo_number - 1] = new_angle
    send_command(servo_number, new_angle)
    if angle_labels[servo_number - 1]:
        angle_labels[servo_number - 1].config(text=f"Angle: {new_angle}")

def set_servo_angle(servo_number, entry):
    try:
        new_angle = int(entry.get())
        if 0 <= new_angle <= 180:
            servo_angles[servo_number - 1] = new_angle
            send_command(servo_number, new_angle)
            if angle_labels[servo_number - 1]:
                angle_labels[servo_number - 1].config(text=f"Angle: {new_angle}")
            if scales[servo_number - 1]:
                scales[servo_number - 1].set(new_angle)
        else:
            print("Angle must be between 0 and 180")
    except ValueError:
        print("Invalid angle value")

def save_coordinates():
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        
        # Read all rows from the CSV file
        rows = []
        with open('save_angles.csv', mode='r') as file:
            reader = csv.reader(file)
            rows = list(reader)
        
        # Check if the coordinate already exists
        coordinate_found = False
        for i, row in enumerate(rows):
            if row:
                saved_x = float(row[0])
                saved_y = float(row[1])
                if abs(saved_x - x) < 0.01 and abs(saved_y - y) < 0.01:  # Using small threshold for float comparison
                    # Overwrite the existing row
                    rows[i] = [x, y] + servo_angles
                    coordinate_found = True
                    break
        
        # If the coordinate was not found, append it
        if not coordinate_found:
            rows.append([x, y] + servo_angles)
        
        # Write all rows back to the CSV file
        with open('save_angles.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(rows)
        
        print(f"Saved coordinates ({x}, {y}) with angles {servo_angles}")
    except ValueError:
        print("Invalid coordinate values")
    except IOError as e:
        print(f"Error saving coordinates: {e}")

def try_coordinates():
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        with open('save_angles.csv', mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    saved_x = float(row[0])
                    saved_y = float(row[1])
                    if saved_x == x and saved_y == y:
                        angles = list(map(int, row[2:]))
                        for i, angle in enumerate(angles):
                            if i != 5:  # Skip servo 6
                                send_command(i + 1, angle)
                                servo_angles[i] = angle
                                if angle_labels[i]:
                                    angle_labels[i].config(text=f"Angle: {angle}")
                                if scales[i]:
                                    scales[i].set(angle)
                                time.sleep(0.5)  # Add a 0.5-second delay between servo movements
                        print(f"Moved to coordinates ({x}, {y}) with angles {angles}")
                        return
            print("Coordinates not found")
    except ValueError:
        print("Invalid coordinate values")
    except IOError as e:
        print(f"Error reading coordinates: {e}")

# Initialize Tkinter
root = tk.Tk()
root.title("Robotic Arm Control")

# Initialize servo angles
servo_angles = [90] * 6

# Initialize servos except servo6
for i in range(1, 6):
    send_command(i, 90)

# Create lists to store controls
angle_labels = []
scales = []

# Create servo controls
for i in range(1, 7):
    scale, angle_label = create_servo_controls(i)
    scales.append(scale)
    angle_labels.append(angle_label)

# Create bottom frame for park button and coordinates
bottom_frame = tk.Frame(root)
bottom_frame.pack(side=tk.BOTTOM, pady=10)

# Create Park button
park_button = tk.Button(bottom_frame, text="Park", command=park_servos)
park_button.pack(side=tk.TOP, pady=5)

# Create coordinate input fields and buttons
coord_frame = tk.Frame(bottom_frame)
coord_frame.pack(side=tk.TOP, pady=5)

x_label = tk.Label(coord_frame, text="X:")
x_label.pack(side=tk.LEFT)
x_entry = tk.Entry(coord_frame, width=5)
x_entry.pack(side=tk.LEFT, padx=5)

y_label = tk.Label(coord_frame, text="Y:")
y_label.pack(side=tk.LEFT)
y_entry = tk.Entry(coord_frame, width=5)
y_entry.pack(side=tk.LEFT, padx=5)

save_button = tk.Button(coord_frame, text="Save Coordinates", command=save_coordinates)
save_button.pack(side=tk.LEFT, padx=5)

try_button = tk.Button(coord_frame, text="Try Coordinates", command=try_coordinates)
try_button.pack(side=tk.LEFT, padx=5)

# Start the Tkinter main loop
root.mainloop()

# Close the serial connection when the window is closed
ser.close()