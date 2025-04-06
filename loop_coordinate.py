import serial
import tkinter as tk
import time
import csv
import threading

SERVO_SEQUENCE = [2, 3, 4, 1]
GET_SERVO_SEQUENCE = [1, 4, 3, 2, 5]
PARK_ANGLES = {
    1: 94,
    2: 77,
    3: 164,
    4: 40,
    5: 90,
    6: 85,
}

servo_angles = [94, 77, 164, 40, 90]
servo_speed = 30
interpolation_delay = 30
coordinate_delay = 3  # variable_1: delay at coordinate position (in seconds)Q
parking_delay = 2  # variable_2: delay at parking position (in seconds)
sequence_running = False

def connect_serial(port='COM6', baudrate=9600):
    try:
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"Connected to {port}")
        return ser
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        return None

def send_command(ser, servo, angle):
    command = f"{servo} {angle}\n"
    ser.write(command.encode())
    response = ser.readline().decode().strip()
    print(f"Sent: {command.strip()} | Response: {response}")
    time.sleep(0.1)

def set_servo_speed(ser, speed):
    command = f"s {speed}\n"
    ser.write(command.encode())
    response = ser.readline().decode().strip()
    print(f"Set speed: {speed} | Response: {response}")

def set_interpolation_delay(ser, delay):
    command = f"i {delay}\n"
    ser.write(command.encode())
    response = ser.readline().decode().strip()
    print(f"Set interpolation delay: {delay} | Response: {response}")

def release_gripper(ser):
    send_command(ser, 6, -1)

def start_gripping(ser):
    send_command(ser, 6, -2)

def move_servos_sequence(ser, angles_dict, sequence=None):
    if sequence is None:
        sequence = SERVO_SEQUENCE
    
    for servo in sequence:
        if servo in angles_dict:
            angle = angles_dict[servo]
            send_command(ser, servo, angle)
            servo_angles[servo - 1] = angle
            if angle_labels[servo - 1]:
                angle_labels[servo - 1].config(text=f"Angle: {angle}")
            if scales[servo - 1]:
                scales[servo - 1].set(angle)
            time.sleep(0.5)

def get_move_servos_sequence(ser, angles_dict, sequence=None):
    if sequence is None:
        sequence = GET_SERVO_SEQUENCE
    
    for servo in sequence:
        if servo in angles_dict:
            angle = angles_dict[servo]
            send_command(ser, servo, angle)
            servo_angles[servo - 1] = angle
            if angle_labels[servo - 1]:
                angle_labels[servo - 1].config(text=f"Angle: {angle}")
            if scales[servo - 1]:
                scales[servo - 1].set(angle)
            time.sleep(0.5)

def park_servos():
    move_servos_sequence(ser, PARK_ANGLES)

def read_coordinates_from_csv(csv_path='sorted_output.csv'):
    coordinates = []
    try:
        with open(csv_path, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) >= 7:  # x, y, and 5 servo angles
                    x = float(row[0])
                    y = float(row[1])
                    angles = {i+1: int(float(row[i+2])) for i in range(5)}
                    coordinates.append((x, y, angles))
        print(f"Loaded {len(coordinates)} coordinates from CSV")
        return coordinates
    except FileNotFoundError:
        print(f"CSV file not found at: {csv_path}")
        return []
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []

def execute_coordinate_sequence(ser, status_label, progress_label):
    global sequence_running
    
    coordinates = read_coordinates_from_csv()
    if not coordinates:
        status_label.config(text="No coordinates found in CSV file")
        sequence_running = False
        return
    
    total_coordinates = len(coordinates)
    current_coordinate = 0
    
    while sequence_running and current_coordinate < total_coordinates:
        x, y, angles = coordinates[current_coordinate]
        
        # Update status display
        status_label.config(text=f"Executing coordinate: ({x}, {y})")
        progress_label.config(text=f"Progress: {current_coordinate + 1}/{total_coordinates}")
        
        # Move to parking position
        park_servos()
        
        # Move to coordinate position
        get_move_servos_sequence(ser, angles)
        
        # Wait at coordinate position (variable_1)
        time.sleep(coordinate_delay)
        
        # Move back to parking position
        park_servos()
        
        # Wait at parking position (variable_2)
        time.sleep(parking_delay)
        
        # Move to next coordinate
        current_coordinate += 1
    
    status_label.config(text="Sequence execution completed" if current_coordinate == total_coordinates else "Sequence stopped")
    sequence_running = False

def start_sequence(ser, start_button, status_label, progress_label):
    global sequence_running
    
    if sequence_running:
        sequence_running = False
        start_button.config(text="Start Sequence")
        status_label.config(text="Sequence stopped")
    else:
        sequence_running = True
        start_button.config(text="Stop Sequence")
        status_label.config(text="Starting sequence...")
        
        # Run the sequence in a separate thread to avoid freezing the GUI
        sequence_thread = threading.Thread(
            target=execute_coordinate_sequence,
            args=(ser, status_label, progress_label)
        )
        sequence_thread.daemon = True
        sequence_thread.start()

def create_servo_controls(root, servo_number, ser):
    frame = tk.Frame(root)
    frame.pack(side=tk.LEFT, padx=10, pady=5)

    label = tk.Label(frame, text=f"Servo {servo_number}")
    label.pack(side=tk.TOP)

    if servo_number == 6:
        grip_frame = tk.Frame(frame)
        grip_frame.pack(side=tk.TOP, pady=5)
        
        open_button = tk.Button(grip_frame, text="Release", 
                              command=lambda: release_gripper(ser))
        open_button.pack(side=tk.LEFT, padx=5)
        
        grip_button = tk.Button(grip_frame, text="Grip", 
                              command=lambda: start_gripping(ser))
        grip_button.pack(side=tk.LEFT, padx=5)
        
        return None, None
    else:
        if servo_number == 1:
            scale = tk.Scale(frame, from_=0, to=180, orient=tk.HORIZONTAL,
                           length=200, command=lambda val, sn=servo_number: 
                           adjust_servo(ser, sn, val))
        else:
            scale = tk.Scale(frame, from_=0, to=180, orient=tk.VERTICAL,
                           length=200, command=lambda val, sn=servo_number: 
                           adjust_servo(ser, sn, val))
            
        scale.set(servo_angles[servo_number - 1])
        scale.pack(side=tk.TOP)

        angle_label = tk.Label(frame, text=f"Angle: {servo_angles[servo_number - 1]}")
        angle_label.pack(side=tk.TOP)
        
        entry_frame = tk.Frame(frame)
        entry_frame.pack(side=tk.TOP, pady=5)
        
        angle_entry = tk.Entry(entry_frame, width=5)
        angle_entry.pack(side=tk.LEFT)
        
        set_button = tk.Button(entry_frame, text="Set", 
                             command=lambda sn=servo_number, e=angle_entry: 
                             set_angle_from_entry(ser, sn, e, scale))
        set_button.pack(side=tk.LEFT, padx=5)

        return scale, angle_label
    
def adjust_servo(ser, servo_number, angle):
    new_angle = int(float(angle))
    
    # Apply limit only to servo3
    if servo_number == 3:
        if new_angle < -20:
            new_angle = -20
        elif new_angle > 180:
            new_angle = 180

    servo_angles[servo_number - 1] = new_angle
    send_command(ser, servo_number, new_angle)
    if angle_labels[servo_number - 1]:
        angle_labels[servo_number - 1].config(text=f"Angle: {new_angle}")

def set_angle_from_entry(ser, servo_number, entry_widget, scale_widget):
    try:
        angle = int(entry_widget.get())

        # Apply limit only to servo3
        if servo_number == 3:
            if angle < -20 or angle > 180:
                print(f"Servo 3 angle must be between -20 and 180 degrees")
                return

        if 0 <= angle <= 180 or (servo_number == 3 and -20 <= angle <= 180):
            scale_widget.set(angle)
        else:
            print(f"Angle must be between 0 and 180 degrees")

    except ValueError:
        print(f"Please enter a valid integer for the angle")

def set_speed_from_entry(ser, entry_widget, scale_widget):
    try:
        speed = int(entry_widget.get())
        if 5 <= speed <= 255:
            scale_widget.set(speed)
            global servo_speed
            servo_speed = speed
            set_servo_speed(ser, speed)
        else:
            print("Speed must be between 5 and 255")
    except ValueError:
        print("Please enter a valid integer for speed")

def set_delay_from_entry(ser, entry_widget, scale_widget):
    try:
        delay = int(entry_widget.get())
        if 10 <= delay <= 200:
            scale_widget.set(delay)
            global interpolation_delay
            interpolation_delay = delay
            set_interpolation_delay(ser, delay)
        else:
            print("Smoothness must be between 10 and 200 ms")
    except ValueError:
        print("Please enter a valid integer for smoothness")

def set_coordinate_delay_from_entry(entry_widget, scale_widget):
    try:
        delay = float(entry_widget.get())
        if 0.1 <= delay <= 30:
            scale_widget.set(delay)
            global coordinate_delay
            coordinate_delay = delay
        else:
            print("Coordinate delay must be between 0.1 and 30 seconds")
    except ValueError:
        print("Please enter a valid number for coordinate delay")

def set_parking_delay_from_entry(entry_widget, scale_widget):
    try:
        delay = float(entry_widget.get())
        if 0.1 <= delay <= 30:
            scale_widget.set(delay)
            global parking_delay
            parking_delay = delay
        else:
            print("Parking delay must be between 0.1 and 30 seconds")
    except ValueError:
        print("Please enter a valid number for parking delay")

def create_settings_controls(root, ser):
    frame = tk.Frame(root)
    frame.pack(side=tk.BOTTOM, pady=10)
    
    # Speed controls
    speed_frame = tk.Frame(frame)
    speed_frame.pack(side=tk.TOP, pady=5)
    
    tk.Label(speed_frame, text="Speed (5-255):").pack(side=tk.LEFT)
    speed_scale = tk.Scale(speed_frame, from_=5, to=255, orient=tk.HORIZONTAL,
                          command=lambda v: set_servo_speed(ser, int(v)))
    speed_scale.set(servo_speed)
    speed_scale.pack(side=tk.LEFT, padx=5)
    
    speed_entry = tk.Entry(speed_frame, width=5)
    speed_entry.insert(0, str(servo_speed))
    speed_entry.pack(side=tk.LEFT, padx=5)
    speed_set_button = tk.Button(speed_frame, text="Set", 
                               command=lambda: set_speed_from_entry(ser, speed_entry, speed_scale))
    speed_set_button.pack(side=tk.LEFT)
    
    # Interpolation delay controls
    delay_frame = tk.Frame(frame)
    delay_frame.pack(side=tk.TOP, pady=5)
    
    tk.Label(delay_frame, text="Smoothness (10-200ms):").pack(side=tk.LEFT)
    delay_scale = tk.Scale(delay_frame, from_=10, to=200, orient=tk.HORIZONTAL,
                          command=lambda v: set_interpolation_delay(ser, int(v)))
    delay_scale.set(interpolation_delay)
    delay_scale.pack(side=tk.LEFT, padx=5)
    
    delay_entry = tk.Entry(delay_frame, width=5)
    delay_entry.insert(0, str(interpolation_delay))
    delay_entry.pack(side=tk.LEFT, padx=5)
    delay_set_button = tk.Button(delay_frame, text="Set", 
                               command=lambda: set_delay_from_entry(ser, delay_entry, delay_scale))
    delay_set_button.pack(side=tk.LEFT)
    
    # Coordinate delay controls (variable_1)
    coord_delay_frame = tk.Frame(frame)
    coord_delay_frame.pack(side=tk.TOP, pady=5)
    
    tk.Label(coord_delay_frame, text="Coord Delay (0.1-30s):").pack(side=tk.LEFT)
    coord_delay_scale = tk.Scale(coord_delay_frame, from_=0.1, to=30, resolution=0.1, orient=tk.HORIZONTAL,
                                command=lambda v: globals().update(coordinate_delay=float(v)))
    coord_delay_scale.set(coordinate_delay)
    coord_delay_scale.pack(side=tk.LEFT, padx=5)
    
    coord_delay_entry = tk.Entry(coord_delay_frame, width=5)
    coord_delay_entry.insert(0, str(coordinate_delay))
    coord_delay_entry.pack(side=tk.LEFT, padx=5)
    coord_delay_set_button = tk.Button(coord_delay_frame, text="Set", 
                                     command=lambda: set_coordinate_delay_from_entry(coord_delay_entry, coord_delay_scale))
    coord_delay_set_button.pack(side=tk.LEFT)
    
    # Parking delay controls (variable_2)
    park_delay_frame = tk.Frame(frame)
    park_delay_frame.pack(side=tk.TOP, pady=5)
    
    tk.Label(park_delay_frame, text="Park Delay (0.1-30s):").pack(side=tk.LEFT)
    park_delay_scale = tk.Scale(park_delay_frame, from_=0.1, to=30, resolution=0.1, orient=tk.HORIZONTAL,
                               command=lambda v: globals().update(parking_delay=float(v)))
    park_delay_scale.set(parking_delay)
    park_delay_scale.pack(side=tk.LEFT, padx=5)
    
    park_delay_entry = tk.Entry(park_delay_frame, width=5)
    park_delay_entry.insert(0, str(parking_delay))
    park_delay_entry.pack(side=tk.LEFT, padx=5)
    park_delay_set_button = tk.Button(park_delay_frame, text="Set", 
                                    command=lambda: set_parking_delay_from_entry(park_delay_entry, park_delay_scale))
    park_delay_set_button.pack(side=tk.LEFT)
    
    # Create sequence status display
    status_frame = tk.Frame(frame)
    status_frame.pack(side=tk.TOP, pady=10)
    
    status_label = tk.Label(status_frame, text="Ready to start sequence", font=("Arial", 12))
    status_label.pack(side=tk.TOP)
    
    progress_label = tk.Label(status_frame, text="", font=("Arial", 10))
    progress_label.pack(side=tk.TOP)
    
    # Create control buttons
    button_frame = tk.Frame(frame)
    button_frame.pack(side=tk.TOP, pady=5)
    
    start_button = tk.Button(button_frame, text="Start Sequence", 
                           command=lambda: start_sequence(ser, start_button, status_label, progress_label))
    start_button.pack(side=tk.LEFT, padx=5)
    
    park_button = tk.Button(button_frame, text="Park", command=park_servos)
    park_button.pack(side=tk.LEFT, padx=5)
    
    return frame, status_label, progress_label

def save_coordinates(x_entry, y_entry, csv_path='save_angles.csv'):
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        updated = False
        rows = []
        
        # Read existing data
        try:
            with open(csv_path, mode='r', newline='') as file:
                reader = csv.reader(file)
                for row in reader:
                    if row and abs(float(row[0]) - x) < 0.01 and abs(float(row[1]) - y) < 0.01:
                        rows.append([x, y] + servo_angles)  # Update existing entry
                        updated = True
                    else:
                        rows.append(row)
        except FileNotFoundError:
            pass  # If file doesn't exist, proceed with writing
        
        # Write updated data
        with open(csv_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(rows)
            if not updated:
                writer.writerow([x, y] + servo_angles)  # Append new entry if no update
        
        print(f"{'Updated' if updated else 'Saved'} position: ({x}, {y}) with angles {servo_angles}")
        
        # After saving, park the servos
        park_servos()
        
        # Wait for 1 second
        time.sleep(1)
        
        # Try the newly saved coordinate
        try_coordinates(ser, x_entry, y_entry, csv_path)
        
    except ValueError as e:
        print(f"Error saving coordinates: {e}")
    except IOError as e:
        print(f"Error accessing file at {csv_path}: {e}")

def try_coordinates(ser, x_entry, y_entry, csv_path='save_angles.csv'):
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        
        with open(csv_path, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row and abs(float(row[0]) - x) < 0.01 and abs(float(row[1]) - y) < 0.01:
                    angles = {i+1: int(float(row[i+2])) for i in range(5)}
                    get_move_servos_sequence(ser, angles)
                    print(f"Moved to coordinates ({x}, {y})")
                    return
                    
        print("Coordinates not found")
    except ValueError as e:
        print(f"Error with coordinates: {e}")
    except FileNotFoundError:
        print(f"CSV file not found at: {csv_path}")

def main():
    global ser, angle_labels, scales
    
    ser = connect_serial()
    if not ser:
        return
    
    root = tk.Tk()
    root.title("Robotic Arm Sequence Controller")
    
    angle_labels = []
    scales = []
    
    for i in range(1, 7):
        scale, angle_label = create_servo_controls(root, i, ser)
        scales.append(scale)
        angle_labels.append(angle_label)
    
    settings_frame, status_label, progress_label = create_settings_controls(root, ser)
    
    coord_frame = tk.Frame(settings_frame)
    coord_frame.pack(side=tk.TOP, pady=5)
    
    tk.Label(coord_frame, text="X:").pack(side=tk.LEFT)
    x_entry = tk.Entry(coord_frame, width=5)
    x_entry.pack(side=tk.LEFT, padx=5)
    
    tk.Label(coord_frame, text="Y:").pack(side=tk.LEFT)
    y_entry = tk.Entry(coord_frame, width=5)
    y_entry.pack(side=tk.LEFT, padx=5)
        
    tk.Button(coord_frame, text="Save Position", 
            command=lambda: save_coordinates(x_entry, y_entry, 'save_angles.csv')).pack(side=tk.LEFT, padx=5)

    tk.Button(coord_frame, text="Try Position", 
            command=lambda: try_coordinates(ser, x_entry, y_entry, 'save_angles.csv')).pack(side=tk.LEFT, padx=5)
    
    root.mainloop()
    
    if ser:
        ser.close()

if __name__ == "__main__":
    main()