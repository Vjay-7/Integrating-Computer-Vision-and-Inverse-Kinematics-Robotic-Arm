import serial
import tkinter as tk
import time
import csv
import os
import threading

# Speed configuration
SPEED_CONFIG = {
    "DEFAULT_SPEED": 60,
    "GRIP_SPEED": 25,
    "RELEASE_SPEED": 50,
    "FAST_SPEED": 100
}

# Configuration for initial parking position and movement parameters
SERVO_CONFIG = {
    1: {"park_angle": 100, "min": 0, "max": 180},  # Base
    2: {"park_angle": 35, "min": 0, "max": 180},   # Shoulder
    3: {"park_angle": 0, "min": 0, "max": 180},    # Elbow
    4: {"park_angle": 180, "min": 0, "max": 180},  # Wrist pitch
    5: {"park_angle": 90, "min": 0, "max": 180},   # Wrist roll
}

# Movement sequence configuration
MOVEMENT_SEQUENCE = [1, 2, 3, 4, 5]  # Order of servo movement
MOVEMENT_DELAY = 0.5  # Delay between servo movements

# Attempt to open the serial port
try:
    ser = serial.Serial('COM8', 9600, timeout=1)
except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
    exit()

def send_speed_command(speed_type, speed_value):
    """
    Send speed update command to Arduino
    speed_type: 1=DEFAULT, 2=GRIP, 3=RELEASE, 4=FAST
    """
    command = f"S{speed_type} {speed_value}\n"
    ser.write(command.encode())
    time.sleep(0.1)
    response = ser.readline().decode().strip()
    print(f"Speed update response: {response}")

def update_speeds():
    """Update all speed settings on the Arduino"""
    speed_type_map = {
        "DEFAULT_SPEED": 1,
        "GRIP_SPEED": 2,
        "RELEASE_SPEED": 3,
        "FAST_SPEED": 4
    }
    
    for speed_name, speed_type in speed_type_map.items():
        send_speed_command(speed_type, SPEED_CONFIG[speed_name])
        time.sleep(0.1)

def create_speed_controls(frame):
    """Create speed control GUI elements"""
    speed_frame = tk.LabelFrame(frame, text="Speed Controls")
    speed_frame.pack(side=tk.BOTTOM, pady=5, padx=5, fill=tk.X)
    
    for speed_name in SPEED_CONFIG:
        row = tk.Frame(speed_frame)
        row.pack(fill=tk.X, padx=5, pady=2)
        
        label = tk.Label(row, text=f"{speed_name}:")
        label.pack(side=tk.LEFT)
        
        entry = tk.Entry(row, width=5)
        entry.insert(0, str(SPEED_CONFIG[speed_name]))
        entry.pack(side=tk.LEFT, padx=5)
        
        def update_command(name=speed_name, ent=entry):
            try:
                value = int(ent.get())
                if 1 <= value <= 255:
                    SPEED_CONFIG[name] = value
                    speed_type_map = {"DEFAULT_SPEED": 1, "GRIP_SPEED": 2, 
                                    "RELEASE_SPEED": 3, "FAST_SPEED": 4}
                    send_speed_command(speed_type_map[name], value)
                else:
                    print("Speed must be between 1 and 255")
            except ValueError:
                print("Invalid speed value")
        
        button = tk.Button(row, text="Update", command=update_command)
        button.pack(side=tk.LEFT, padx=5)

def send_command(servo, angle):
    """Send command to move servo to a specific angle"""
    command = f"{servo} {angle}\n"
    ser.write(command.encode())
    time.sleep(0.1)

def release_gripper():
    """Release the gripper"""
    command = "6 -1\n"
    ser.write(command.encode())
    time.sleep(0.1)

def start_gripping():
    """Start gripping"""
    command = "6 -2\n"
    ser.write(command.encode())
    time.sleep(0.1)

def execute_get_sequence():
    """Execute the sequence to get an item"""
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        
        # Move to target coordinates
        target_found = False
        target_angles = {}
        
        with open('save_angles.csv', mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    saved_x = float(row[0])
                    saved_y = float(row[1])
                    if abs(saved_x - x) < 0.01 and abs(saved_y - y) < 0.01:
                        angles = list(map(int, row[2:7]))
                        target_angles = {i+1: angle for i, angle in enumerate(angles)}
                        target_found = True
                        break
        
        if not target_found:
            print("Coordinates not found in saved positions!")
            return
            
        move_servos_sequence(target_angles)
        time.sleep(1)
        
        # Grip the item
        print("Gripping item...")
        start_gripping()
        time.sleep(1.5)
        
        # Move to park position
        print("Returning to park position...")
        park_servos()
        
        print("Sequence complete!")
        
    except ValueError as e:
        print(f"Error with coordinates: {e}")
    except IOError as e:
        print(f"Error reading coordinates file: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def get_item():
    """Run the sequence in a separate thread to keep GUI responsive"""
    thread = threading.Thread(target=execute_get_sequence)
    thread.daemon = True
    thread.start()

def create_gripper_controls(frame):
    """Create controls for the gripper (servo 6)"""
    grip_frame = tk.Frame(frame)
    grip_frame.pack(side=tk.TOP, pady=5)
    
    open_button = tk.Button(grip_frame, text="Release", command=release_gripper)
    open_button.pack(side=tk.LEFT, padx=5)
    
    grip_button = tk.Button(grip_frame, text="Grip", command=start_gripping)
    grip_button.pack(side=tk.LEFT, padx=5)
    
    get_button = tk.Button(grip_frame, text="Get Item", command=get_item)
    get_button.pack(side=tk.LEFT, padx=5)

def move_servos_sequence(target_angles_dict):
    """Move servos in sequence with configurable delay"""
    for servo in MOVEMENT_SEQUENCE:
        if servo in target_angles_dict:
            target_angle = target_angles_dict[servo]
            send_command(servo, target_angle)
            
            # Update GUI
            servo_angles[servo - 1] = target_angle
            if angle_labels[servo - 1]:
                angle_labels[servo - 1].config(text=f"Angle: {target_angle}")
            if scales[servo - 1]:
                scales[servo - 1].set(target_angle)
                
            time.sleep(MOVEMENT_DELAY)

def try_coordinates():
    """Try to move to the specified coordinates"""
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        
        with open('save_angles.csv', mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    saved_x = float(row[0])
                    saved_y = float(row[1])
                    if abs(saved_x - x) < 0.01 and abs(saved_y - y) < 0.01:
                        angles = list(map(int, row[2:7]))
                        target_angles = {i+1: angle for i, angle in enumerate(angles)}
                        move_servos_sequence(target_angles)
                        print(f"Moved to coordinates ({x}, {y}) with angles {angles}")
                        return
            print("Coordinates not found")
    except ValueError:
        print("Invalid coordinate values")
    except IOError as e:
        print(f"Error reading coordinates: {e}")

def save_coordinates():
    """Save the current coordinates and angles to a file"""
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        
        rows = []
        with open('save_angles.csv', mode='r') as file:
            reader = csv.reader(file)
            rows = list(reader)
        
        coordinate_found = False
        for i, row in enumerate(rows):
            if row:
                saved_x = float(row[0])
                saved_y = float(row[1])
                if abs(saved_x - x) < 0.01 and abs(saved_y - y) < 0.01:
                    rows[i] = [x, y] + servo_angles
                    coordinate_found = True
                    break
        
        if not coordinate_found:
            rows.append([x, y] + servo_angles)
        
        with open('save_angles.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(rows)
        
        print(f"Saved coordinates ({x}, {y}) with angles {servo_angles}")
    except ValueError:
        print("Invalid coordinate values")
    except IOError as e:
        print(f"Error saving coordinates: {e}")

def park_servos():
    """Move to parking position"""
    park_angles = {servo: config["park_angle"] for servo, config in SERVO_CONFIG.items()}
    move_servos_sequence(park_angles)

def create_servo_controls(servo_number):
    """Create controls for a specific servo"""
    frame = tk.Frame(root)
    frame.pack(side=tk.LEFT, padx=10, pady=5)

    label = tk.Label(frame, text=f"Servo {servo_number}")
    label.pack(side=tk.TOP)

    if servo_number == 6:
        create_gripper_controls(frame)
        return None, None
    else:
        config = SERVO_CONFIG[servo_number]
        scale = tk.Scale(frame, from_=config["min"], to=config["max"],
                        orient=tk.VERTICAL if servo_number in [2, 3, 4] else tk.HORIZONTAL,
                        length=200, command=lambda val, sn=servo_number: adjust_servo(sn, val))
        
        scale.set(config["park_angle"])
        scale.pack(side=tk.TOP)

        angle_label = tk.Label(frame, text=f"Angle: {config['park_angle']}")
        angle_label.pack(side=tk.TOP)

        entry = tk.Entry(frame, width=5)
        entry.pack(side=tk.TOP, pady=5)
        
        button = tk.Button(frame, text="Set Angle", 
                          command=lambda sn=servo_number, ent=entry: set_servo_angle(sn, ent))
        button.pack(side=tk.TOP)

        return scale, angle_label

def adjust_servo(servo_number, angle):
    """Adjust the servo to a specific angle"""
    new_angle = int(float(angle))
    servo_angles[servo_number - 1] = new_angle
    send_command(servo_number, new_angle)
    if angle_labels[servo_number - 1]:
        angle_labels[servo_number - 1].config(text=f"Angle: {new_angle}")

def set_servo_angle(servo_number, entry):
    """Set the servo angle based on the entry field"""
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

# Initialize Tkinter
root = tk.Tk()
root.title("Robotic Arm Control")

# Initialize servo angles with parking positions
servo_angles = [SERVO_CONFIG[i]["park_angle"] for i in range(1, 6)] + [90]  # Add servo 6 default

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

create_speed_controls(bottom_frame)
update_speeds()

# Initialize servos to parking position when starting
park_servos()

# Start the Tkinter main loop
root.mainloop()

# Close the serial connection when the window is closed
ser.close()