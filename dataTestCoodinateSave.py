import serial
import tkinter as tk
import time
import csv
import threading

# Configuration
SERVO_SEQUENCE = [1, 2, 4, 3, 5]  # Sequence for coordinated movements
GET_SERVO_SEQUENCE = [1, 2, 3, 4, 5]  # Sequence for getting an item
PARK_ANGLES = {
    1: 100,  # Base
    2: 45,  # Shoulder
    3: 0,  # Elbow
    4: 180,  # Wrist pitch
    5: 90,  # Wrist roll
}

# Global variables
servo_angles = [90] * 6
servo_speed = 35
interpolation_delay = 50

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

def create_servo_controls(root, servo_number, ser):
    frame = tk.Frame(root)
    frame.pack(side=tk.LEFT, padx=10, pady=5)

    label = tk.Label(frame, text=f"Servo {servo_number}")
    label.pack(side=tk.TOP)

    if servo_number == 6:
        # Gripper controls
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
        # Regular servo controls
        scale = tk.Scale(frame, from_=0, to=180, orient=tk.VERTICAL,
                        length=200, command=lambda val, sn=servo_number: 
                        adjust_servo(ser, sn, val))
        scale.set(servo_angles[servo_number - 1])
        scale.pack(side=tk.TOP)

        angle_label = tk.Label(frame, text=f"Angle: {servo_angles[servo_number - 1]}")
        angle_label.pack(side=tk.TOP)

        return scale, angle_label

def adjust_servo(ser, servo_number, angle):
    new_angle = int(float(angle))
    servo_angles[servo_number - 1] = new_angle
    send_command(ser, servo_number, new_angle)
    if angle_labels[servo_number - 1]:
        angle_labels[servo_number - 1].config(text=f"Angle: {new_angle}")

def create_settings_controls(root, ser):
    frame = tk.Frame(root)
    frame.pack(side=tk.BOTTOM, pady=10)
    
    # Speed control
    speed_frame = tk.Frame(frame)
    speed_frame.pack(side=tk.TOP, pady=5)
    
    tk.Label(speed_frame, text="Speed (5-255):").pack(side=tk.LEFT)
    speed_scale = tk.Scale(speed_frame, from_=5, to=255, orient=tk.HORIZONTAL,
                          command=lambda v: set_servo_speed(ser, int(v)))
    speed_scale.set(servo_speed)
    speed_scale.pack(side=tk.LEFT, padx=5)
    
    # Interpolation delay control
    delay_frame = tk.Frame(frame)
    delay_frame.pack(side=tk.TOP, pady=5)
    
    tk.Label(delay_frame, text="Smoothness (10-200ms):").pack(side=tk.LEFT)
    delay_scale = tk.Scale(delay_frame, from_=10, to=200, orient=tk.HORIZONTAL,
                          command=lambda v: set_interpolation_delay(ser, int(v)))
    delay_scale.set(interpolation_delay)
    delay_scale.pack(side=tk.LEFT, padx=5)
    
    return frame

def save_coordinates(x_entry, y_entry):
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        
        with open('save_angles.csv', mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([x, y] + servo_angles)
            
        print(f"Saved position: ({x}, {y}) with angles {servo_angles}")
    except ValueError as e:
        print(f"Error saving coordinates: {e}")

def try_coordinates(ser, x_entry, y_entry):
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        
        with open('save_angles.csv', mode='r') as file:
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

def main():
    global ser, angle_labels, scales
    
    # Initialize serial connection
    ser = connect_serial()
    if not ser:
        return
    
    # Create main window
    root = tk.Tk()
    root.title("Robotic Arm Control")
    
    # Initialize control lists
    angle_labels = []
    scales = []
    
    # Create servo controls
    for i in range(1, 7):
        scale, angle_label = create_servo_controls(root, i, ser)
        scales.append(scale)
        angle_labels.append(angle_label)
    
    # Create settings controls
    settings_frame = create_settings_controls(root, ser)
    
    # Create coordinate controls
    coord_frame = tk.Frame(settings_frame)
    coord_frame.pack(side=tk.TOP, pady=5)
    
    tk.Label(coord_frame, text="X:").pack(side=tk.LEFT)
    x_entry = tk.Entry(coord_frame, width=5)
    x_entry.pack(side=tk.LEFT, padx=5)
    
    tk.Label(coord_frame, text="Y:").pack(side=tk.LEFT)
    y_entry = tk.Entry(coord_frame, width=5)
    y_entry.pack(side=tk.LEFT, padx=5)
    
    tk.Button(coord_frame, text="Save Position", 
              command=lambda: save_coordinates(x_entry, y_entry)).pack(side=tk.LEFT, padx=5)
    
    tk.Button(coord_frame, text="Try Position", 
              command=lambda: try_coordinates(ser, x_entry, y_entry)).pack(side=tk.LEFT, padx=5)
    
    # Create park button
    tk.Button(settings_frame, text="Park", command=park_servos).pack(side=tk.TOP, pady=5)
    
    # Start the application
    root.mainloop()
    
    # Clean up
    if ser:
        ser.close()

if __name__ == "__main__":
    main()