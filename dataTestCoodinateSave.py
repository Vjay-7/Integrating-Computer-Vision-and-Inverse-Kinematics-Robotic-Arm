import serial
import tkinter as tk
import time
import csv
import os

# Attempt to open the serial port
try:
    ser = serial.Serial('COM8', 9600, timeout=1)  # Replace 'COM8' with the correct port for your system
except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
    exit()

# Function to send the command to the Arduino
def send_command(servo, angle):
    command = f"{servo} {angle}\n"
    ser.write(command.encode())
    time.sleep(0.1)  # Allow some time for the Arduino to process the command

# Function to create controls for each servo
def create_servo_controls(servo_number):
    frame = tk.Frame(root)
    frame.pack(side=tk.TOP, padx=10, pady=5)

    label = tk.Label(frame, text=f"Servo {servo_number}")
    label.pack(side=tk.LEFT)

    scale = tk.Scale(frame, from_=0, to=180, orient=tk.HORIZONTAL, command=lambda val, sn=servo_number: adjust_servo(sn, val))
    scale.set(servo_angles[servo_number - 1])
    scale.pack(side=tk.LEFT)

    angle_label = tk.Label(frame, text=f"Angle: {servo_angles[servo_number - 1]}")
    angle_label.pack(side=tk.LEFT)
    
    entry = tk.Entry(frame, width=5)
    entry.pack(side=tk.LEFT, padx=5)
    
    button = tk.Button(frame, text="Set Angle", command=lambda sn=servo_number, ent=entry: set_servo_angle(sn, ent))
    button.pack(side=tk.LEFT)

    return scale, angle_label

# Function to adjust the angle of a servo using the scale
def adjust_servo(servo_number, angle):
    global servo_angles, angle_labels
    new_angle = int(angle)
    servo_angles[servo_number - 1] = new_angle
    send_command(servo_number, new_angle)
    angle_labels[servo_number - 1].config(text=f"Angle: {new_angle}")

# Function to set the servo angle using the input field
def set_servo_angle(servo_number, entry):
    global servo_angles, angle_labels
    try:
        new_angle = int(entry.get())
        if 0 <= new_angle <= 180:
            servo_angles[servo_number - 1] = new_angle
            send_command(servo_number, new_angle)
            angle_labels[servo_number - 1].config(text=f"Angle: {new_angle}")
            scales[servo_number - 1].set(new_angle)
        else:
            print("Angle must be between 0 and 180")
    except ValueError:
        print("Invalid angle value")

# Function to save servo angles and coordinates to a CSV file
def save_coordinates():
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        with open('D:/3rd Year Files/Thesis/servo_angles.csv', mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([x, y] + servo_angles)
        print(f"Saved coordinates ({x}, {y}) with angles {servo_angles}")
    except ValueError:
        print("Invalid coordinate value")
    except IOError as e:
        print(f"Error saving coordinates: {e}")

# Function to park all servos at 90 degrees, S4 at 75 degrees
def park_servos():
    park_sequence = [3, 2, 1, 4, 5, 6]
    for servo in park_sequence:
        
        angle = 60 if servo == 4 else 90
        send_command(servo, angle)
        servo_angles[servo - 1] = angle
        angle_labels[servo - 1].config(text=f"Angle: {angle}")
        scales[servo - 1].set(angle)

# Function to navigate to saved coordinates 
def try_coordinates():
    try:
        x = float(x_entry.get())
        y = float(y_entry.get())
        with open('D:/3rd Year Files/Thesis/servo_angles.csv', mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row:
                    saved_x = float(row[0])
                    saved_y = float(row[1])
                    if saved_x == x and saved_y == y:
                        angles = list(map(int, row[2:]))
                        for i, angle in enumerate(angles):
                            send_command(i + 1, angle)
                            servo_angles[i] = angle
                            angle_labels[i].config(text=f"Angle: {angle}")
                            scales[i].set(angle)
                        print(f"Moved to coordinates ({x}, {y}) with angles {angles}")
                        return
        print("Coordinates not found")
    except ValueError:
        print("Invalid coordinate value")
    except IOError as e:
        print(f"Error reading coordinates: {e}")

# Initialize Tkinter
root = tk.Tk()
root.title("Servo Control")

# Initialize servo angles
servo_angles = [90] * 6

# Create a list to store angle labels and scales
angle_labels = []
scales = []

# Create servo controls
for i in range(1, 7):
    scale, angle_label = create_servo_controls(i)
    scales.append(scale)
    angle_labels.append(angle_label)

# Create Park button
park_button = tk.Button(root, text="Park", command=park_servos)
park_button.pack(pady=10)

# Create coordinate input fields and buttons
coord_frame = tk.Frame(root)
coord_frame.pack(pady=10)

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
