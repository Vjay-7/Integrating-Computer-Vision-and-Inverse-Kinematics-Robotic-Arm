import serial
import tkinter as tk
import time
import csv
import threading

# Constants
SERVO_SEQUENCE = [2, 1, 3, 4, 5]  # Updated sequence for moving to end coordinate
GET_SERVO_SEQUENCE = [1, 4, 3, 2, 5]  # Sequence for getting to start position
PARK_ANGLES = {
    1: 94,
    2: 77,
    3: 164,
    4: 40,
    5: 90,
    6: 85,
}

# Gripper settings
GRIPPER_SERVO = 6
GRIPPER_OPEN_ANGLE = 30
GRIPPER_CLOSED_ANGLE = 85
gripper_state = False  # False = closed, True = open

# Global variables
servo_angles = [94, 77, 164, 40, 90, 85] 
interpolation_delay = 30
servo_speed = 100  # Added this missing global variable
movement_running = False

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

def move_servos_sequence(ser, angles_dict, sequence=None):
    if sequence is None:
        sequence = SERVO_SEQUENCE
    
    for servo in sequence:
        if servo in angles_dict:
            angle = angles_dict[servo]
            send_command(ser, servo, angle)
            servo_angles[servo - 1] = angle
            time.sleep(0.5)

def get_move_servos_sequence(ser, angles_dict, sequence=None):
    if sequence is None:
        sequence = GET_SERVO_SEQUENCE
    
    for servo in sequence:
        if servo in angles_dict:
            angle = angles_dict[servo]
            send_command(ser, servo, angle)
            servo_angles[servo - 1] = angle
            time.sleep(0.5)

def toggle_gripper(ser, gripper_button, status_label, force_state=None):
    global gripper_state
    
    if force_state is not None:
        gripper_state = force_state
    else:
        gripper_state = not gripper_state
    
    if gripper_state:  # Open the gripper
        send_command(ser, GRIPPER_SERVO, GRIPPER_OPEN_ANGLE)
        servo_angles[GRIPPER_SERVO - 1] = GRIPPER_OPEN_ANGLE  # Fixed this line
        gripper_button.config(text="Close Gripper")
        status_label.config(text="Gripper opened")
    else:  # Close the gripper
        send_command(ser, GRIPPER_SERVO, GRIPPER_CLOSED_ANGLE)
        servo_angles[GRIPPER_SERVO - 1] = GRIPPER_CLOSED_ANGLE  # Fixed this line
        gripper_button.config(text="Open Gripper")
        status_label.config(text="Gripper closed")

def park_servos(ser):
    move_servos_sequence(ser, PARK_ANGLES)

def get_coordinates_from_csv(x, y, csv_path='save_angles.csv'):
    try:
        with open(csv_path, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row and abs(float(row[0]) - x) < 0.01 and abs(float(row[1]) - y) < 0.01:
                    angles = {i+1: int(float(row[i+2])) for i in range(5)}
                    return angles
        return None
    except FileNotFoundError:
        print(f"CSV file not found at: {csv_path}")
        return None
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None

def move_to_coordinate(ser, x, y, status_label, sequence=None):
    angles = get_coordinates_from_csv(x, y)
    if angles:
        status_label.config(text=f"Moving to: ({x}, {y})")
        if sequence:
            move_servos_sequence(ser, angles, sequence)
        else:
            get_move_servos_sequence(ser, angles)
        return True
    else:
        status_label.config(text=f"Coordinate ({x}, {y}) not found in database")
        return False

def execute_coordinate_cycling(ser, start_x, start_y, end_x, end_y, cycles, status_label, progress_label, start_button, gripper_button):
    global movement_running
    
    try:
        current_cycle = 1
        
        while movement_running and current_cycle <= cycles:
            # Update progress display
            progress_label.config(text=f"Progress: Cycle {current_cycle}/{cycles}")
            
            # 1. Move to park position
            status_label.config(text="Moving to park position")
            park_servos(ser)
            time.sleep(1)
            
            # 2. Move to start coordinate
            if not move_to_coordinate(ser, start_x, start_y, status_label):
                break
            time.sleep(1)
            
            # 3. Close the gripper
            status_label.config(text="Closing gripper")
            toggle_gripper(ser, gripper_button, status_label, force_state=False)
            time.sleep(1)
            
            # 4. Move to end coordinate with specific sequence
            if not move_to_coordinate(ser, end_x, end_y, status_label, sequence=SERVO_SEQUENCE):
                break
            time.sleep(1)
            
            # 5. Open/release the gripper
            status_label.config(text="Opening gripper")
            toggle_gripper(ser, gripper_button, status_label, force_state=True)
            time.sleep(3)
            
            # 6. Move back to park position
            status_label.config(text="Returning to park position")
            park_servos(ser)
            time.sleep(1)
            
            # Increment cycle
            current_cycle += 1
        
        status_label.config(text="Cycle execution completed" if current_cycle > cycles else "Cycle execution stopped")
        movement_running = False
        start_button.config(text="Start")
        
    except Exception as e:
        status_label.config(text=f"Error: {str(e)}")
        movement_running = False
        start_button.config(text="Start")

def start_stop_cycling(ser, start_button, status_label, progress_label, gripper_button,
                     start_x_entry, start_y_entry, end_x_entry, end_y_entry, cycles_entry):
    global movement_running
    
    if movement_running:
        movement_running = False
        start_button.config(text="Start")
        status_label.config(text="Cycling stopped")
    else:
        try:
            start_x = float(start_x_entry.get())
            start_y = float(start_y_entry.get())
            end_x = float(end_x_entry.get())
            end_y = float(end_y_entry.get())
            cycles = int(cycles_entry.get())
            
            if cycles <= 0:
                status_label.config(text="Cycles must be greater than 0")
                return
                
            movement_running = True
            start_button.config(text="Stop")
            status_label.config(text="Starting coordinate cycling...")
            
            # Run the sequence in a separate thread to avoid freezing the GUI
            cycle_thread = threading.Thread(
                target=execute_coordinate_cycling,
                args=(ser, start_x, start_y, end_x, end_y, cycles, status_label, progress_label, start_button, gripper_button)
            )
            cycle_thread.daemon = True
            cycle_thread.start()
            
        except ValueError:
            status_label.config(text="Please enter valid numbers for coordinates and cycles")

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

def try_coordinates(ser, x_entry, y_entry, status_label):
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        
        angles = get_coordinates_from_csv(x, y)
        if angles:
            get_move_servos_sequence(ser, angles)
            status_label.config(text=f"Moved to coordinates ({x}, {y})")
        else:
            status_label.config(text=f"Coordinates ({x}, {y}) not found")
    except ValueError as e:
        status_label.config(text=f"Error with coordinates: {e}")

def create_main_ui(root, ser):
    global servo_speed, interpolation_delay
    
    # Create main frame
    main_frame = tk.Frame(root, padx=10, pady=10)
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Create coordinate input section
    coord_frame = tk.Frame(main_frame, bd=2, relief=tk.GROOVE, padx=10, pady=10)
    coord_frame.pack(fill=tk.X, padx=5, pady=5)
    
    tk.Label(coord_frame, text="Coordinate Cycling", font=("Arial", 12, "bold")).pack(pady=5)
    
    # Start coordinate
    start_coord_frame = tk.Frame(coord_frame)
    start_coord_frame.pack(fill=tk.X, pady=5)
    
    tk.Label(start_coord_frame, text="Start Coordinate:", width=15, anchor=tk.W).pack(side=tk.LEFT)
    tk.Label(start_coord_frame, text="X:").pack(side=tk.LEFT)
    start_x_entry = tk.Entry(start_coord_frame, width=6)
    start_x_entry.pack(side=tk.LEFT, padx=2)
    
    tk.Label(start_coord_frame, text="Y:").pack(side=tk.LEFT, padx=(10, 0))
    start_y_entry = tk.Entry(start_coord_frame, width=6)
    start_y_entry.pack(side=tk.LEFT, padx=2)
    
    # End coordinate
    end_coord_frame = tk.Frame(coord_frame)
    end_coord_frame.pack(fill=tk.X, pady=5)
    
    tk.Label(end_coord_frame, text="End Coordinate:", width=15, anchor=tk.W).pack(side=tk.LEFT)
    tk.Label(end_coord_frame, text="X:").pack(side=tk.LEFT)
    end_x_entry = tk.Entry(end_coord_frame, width=6)
    end_x_entry.pack(side=tk.LEFT, padx=2)
    
    tk.Label(end_coord_frame, text="Y:").pack(side=tk.LEFT, padx=(10, 0))
    end_y_entry = tk.Entry(end_coord_frame, width=6)
    end_y_entry.pack(side=tk.LEFT, padx=2)
    
    # Cycles
    cycles_frame = tk.Frame(coord_frame)
    cycles_frame.pack(fill=tk.X, pady=5)
    
    tk.Label(cycles_frame, text="Cycles:", width=15, anchor=tk.W).pack(side=tk.LEFT)
    cycles_entry = tk.Entry(cycles_frame, width=6)
    cycles_entry.insert(0, "1")
    cycles_entry.pack(side=tk.LEFT, padx=2)
    
    # Create status display
    status_frame = tk.Frame(coord_frame)
    status_frame.pack(fill=tk.X, pady=10)
    
    status_label = tk.Label(status_frame, text="Ready", font=("Arial", 10))
    status_label.pack(side=tk.TOP, fill=tk.X)
    
    progress_label = tk.Label(status_frame, text="", font=("Arial", 10))
    progress_label.pack(side=tk.TOP, fill=tk.X)
    
    # Create control buttons
    button_frame = tk.Frame(coord_frame)
    button_frame.pack(fill=tk.X, pady=5)
    
    # Add gripper control button (declare it first so we can pass it to start_stop_cycling)
    gripper_button = tk.Button(button_frame, text="Open Gripper", width=15, bg="lightgreen",
                            command=lambda: toggle_gripper(ser, gripper_button, status_label))
    
    start_button = tk.Button(button_frame, text="Start", width=10,
                          command=lambda: start_stop_cycling(
                              ser, start_button, status_label, progress_label, gripper_button,
                              start_x_entry, start_y_entry, end_x_entry, end_y_entry, cycles_entry))
    start_button.pack(side=tk.LEFT, padx=5)
    
    park_button = tk.Button(button_frame, text="Park", width=10,
                          command=lambda: park_servos(ser))
    park_button.pack(side=tk.LEFT, padx=5)
    
    try_button = tk.Button(button_frame, text="Try Coordinate", width=15,
                         command=lambda: try_coordinates(ser, start_x_entry, start_y_entry, status_label))
    try_button.pack(side=tk.LEFT, padx=5)
    
    # Now place the gripper button
    gripper_button.pack(side=tk.LEFT, padx=5)
    
    # Create settings section
    settings_frame = tk.Frame(main_frame, bd=2, relief=tk.GROOVE, padx=10, pady=10)
    settings_frame.pack(fill=tk.X, padx=5, pady=10)
    
    tk.Label(settings_frame, text="Settings", font=("Arial", 12, "bold")).pack(pady=5)
    
    # Speed controls
    speed_frame = tk.Frame(settings_frame)
    speed_frame.pack(fill=tk.X, pady=5)
    
    tk.Label(speed_frame, text="Speed (5-255):", width=15, anchor=tk.W).pack(side=tk.LEFT)
    speed_scale = tk.Scale(speed_frame, from_=5, to=255, orient=tk.HORIZONTAL,
                         command=lambda v: set_servo_speed(ser, int(v)))
    speed_scale.set(servo_speed)
    speed_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    
    speed_entry = tk.Entry(speed_frame, width=5)
    speed_entry.insert(0, str(servo_speed))
    speed_entry.pack(side=tk.LEFT, padx=5)
    
    speed_set_button = tk.Button(speed_frame, text="Set", 
                               command=lambda: set_speed_from_entry(ser, speed_entry, speed_scale))
    speed_set_button.pack(side=tk.LEFT)
    
    # Interpolation delay controls
    delay_frame = tk.Frame(settings_frame)
    delay_frame.pack(fill=tk.X, pady=5)
    
    tk.Label(delay_frame, text="Smoothness (10-200ms):", width=15, anchor=tk.W).pack(side=tk.LEFT)
    delay_scale = tk.Scale(delay_frame, from_=10, to=200, orient=tk.HORIZONTAL,
                         command=lambda v: set_interpolation_delay(ser, int(v)))
    delay_scale.set(interpolation_delay)
    delay_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    
    delay_entry = tk.Entry(delay_frame, width=5)
    delay_entry.insert(0, str(interpolation_delay))
    delay_entry.pack(side=tk.LEFT, padx=5)
    
    delay_set_button = tk.Button(delay_frame, text="Set", 
                               command=lambda: set_delay_from_entry(ser, delay_entry, delay_scale))
    delay_set_button.pack(side=tk.LEFT)
    
    # Create gripper settings frame
    gripper_settings_frame = tk.Frame(main_frame, bd=2, relief=tk.GROOVE, padx=10, pady=10)
    gripper_settings_frame.pack(fill=tk.X, padx=5, pady=10)
    
    tk.Label(gripper_settings_frame, text="Gripper Settings", font=("Arial", 12, "bold")).pack(pady=5)
    
    # Open angle setting
    open_angle_frame = tk.Frame(gripper_settings_frame)
    open_angle_frame.pack(fill=tk.X, pady=5)
    
    tk.Label(open_angle_frame, text="Open Angle:", width=15, anchor=tk.W).pack(side=tk.LEFT)
    open_angle_scale = tk.Scale(open_angle_frame, from_=0, to=180, orient=tk.HORIZONTAL,
                              command=lambda v: globals().update({'GRIPPER_OPEN_ANGLE': int(v)}))
    open_angle_scale.set(GRIPPER_OPEN_ANGLE)
    open_angle_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    
    # Closed angle setting
    closed_angle_frame = tk.Frame(gripper_settings_frame)
    closed_angle_frame.pack(fill=tk.X, pady=5)
    
    tk.Label(closed_angle_frame, text="Closed Angle:", width=15, anchor=tk.W).pack(side=tk.LEFT)
    closed_angle_scale = tk.Scale(closed_angle_frame, from_=0, to=180, orient=tk.HORIZONTAL,
                                command=lambda v: globals().update({'GRIPPER_CLOSED_ANGLE': int(v)}))
    closed_angle_scale.set(GRIPPER_CLOSED_ANGLE)
    closed_angle_scale.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
    
    return status_label, progress_label

def main():
    ser = connect_serial()
    if not ser:
        print("Failed to connect to serial port")
        return
    
    root = tk.Tk()
    root.title("Robot Coordinate Cycler")
    root.geometry("600x550")
    
    status_label, progress_label = create_main_ui(root, ser)
    
    set_servo_speed(ser, servo_speed)
    set_interpolation_delay(ser, interpolation_delay)
    
    root.mainloop()
    
    if ser:
        ser.close()

if __name__ == "__main__":
    main()