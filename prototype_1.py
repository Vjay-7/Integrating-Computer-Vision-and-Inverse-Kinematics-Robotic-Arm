import cv2
import numpy as np
from ultralytics import YOLO
import serial
import time
import csv
import threading
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# Robotic arm constants
SERVO_SEQUENCE = [2, 3, 4, 1]
GET_SERVO_SEQUENCE = [1, 4, 3, 2, 5]
PARK_ANGLES = {
    1: 94,
    2: 77,
    3: 164,
    4: 40,
    5: 90,
}

# Predefined bin positions
BIN_POSITIONS = {
    "blue": {1: 141, 2: 114, 3: 133, 4: 153, 5: 90},    # Biodegradable
    "black": {1: 94, 2: 96, 3: 133, 4: 153, 5: 90},   # Non-biodegradable
    "red": {1: 57, 2: 114, 3: 133, 4: 153, 5: 90}       # Recyclable
}

# Computer vision constants
CLASS_MAPPING = {
    0: {"name": "Non-biodegradable", "bin": "black", "priority": 2, "color": (0, 0, 255)},  # Red
    1: {"name": "Biodegradable", "bin": "blue", "priority": 1, "color": (0, 255, 0)},      # Green
    2: {"name": "Recyclable", "bin": "red", "priority": 3, "color": (255, 255, 0)}        # Yellow
}

# Global variables
servo_angles = [94, 77, 164, 40, 90, 80]
servo_speed = 30
interpolation_delay = 15
processing_active = False
app = None
video_label = None
update_frame_event = threading.Event()

# Serial connection functions
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
    print("Gripper released")

def start_gripping(ser):
    send_command(ser, 6, -2)
    print("Gripper closed")

def move_servos_sequence(ser, angles_dict, sequence=None):
    if sequence is None:
        sequence = SERVO_SEQUENCE
    
    for servo in sequence:
        if servo in angles_dict:
            angle = angles_dict[servo]
            send_command(ser, servo, angle)
            if servo <= 5:  # Update servo_angles only for servos 1-5
                servo_angles[servo - 1] = angle
            time.sleep(0.5)

def get_move_servos_sequence(ser, angles_dict, sequence=None):
    if sequence is None:
        sequence = GET_SERVO_SEQUENCE
    
    for servo in sequence:
        if servo in angles_dict:
            angle = angles_dict[servo]
            send_command(ser, servo, angle)
            if servo <= 5:  # Update servo_angles only for servos 1-5
                servo_angles[servo - 1] = angle
            time.sleep(0.5)

def move_to_bin(ser, bin_color):
    print(f"Moving to {bin_color} bin")
    move_servos_sequence(ser, BIN_POSITIONS[bin_color])

def park_servos(ser):
    print("Moving to parking position")
    move_servos_sequence(ser, PARK_ANGLES)
    
# Computer Vision functions
def get_coordinate_from_pixel(pixel_x, pixel_y, center_x, center_y, unit_pixel, scale):
    grid_x = round((pixel_x - center_x) / unit_pixel)
    grid_y = round((center_y - pixel_y) / unit_pixel)
    return grid_x, grid_y

def detect_objects(frame, model, scale=1):
    height, width = frame.shape[:2]
    center_x, center_y = width // 2, height // 2
    unit_pixel = min(width, height) // (4 * scale)
    
    results = model(frame, conf=0.5)
    detections = []
    
    if results and len(results) > 0:
        result = results[0]
        class_counts = {0: 1, 1: 1, 2: 1}  # Track object counts per class
        
        for i, box in enumerate(result.boxes.xyxy):
            x1, y1, x2, y2 = map(int, box)
            center_point_x = (x1 + x2) // 2
            center_point_y = (y1 + y2) // 2
            grid_x, grid_y = get_coordinate_from_pixel(center_point_x, center_point_y, center_x, center_y, unit_pixel, scale)
            
            obj_width, obj_height = x2 - x1, y2 - y1
            orientation = "horizontal" if obj_width > obj_height else "vertical"
            
            class_id = int(result.boxes.cls[i])
            
            if class_id in CLASS_MAPPING:
                class_info = CLASS_MAPPING[class_id]
                obj_id = f"{class_info['name'].lower().replace('-', '_')}_{class_counts[class_id]}"
                class_counts[class_id] += 1
                
                detection = {
                    "id": obj_id,
                    "class_id": class_id,
                    "name": class_info["name"],
                    "bin": class_info["bin"],
                    "priority": class_info["priority"],
                    "x": grid_x,
                    "y": grid_y,
                    "orientation": orientation,
                    "box": (x1, y1, x2, y2),  # Store bounding box coordinates
                    "confidence": float(result.boxes.conf[i])
                }
                
                detections.append(detection)
    
    # Sort detections by priority
    detections.sort(key=lambda x: x["priority"])
    
    return detections

def try_coordinates(ser, x, y, orientation, csv_path='save_angles_update.csv'):
    """Move robot arm to specified coordinates and adjust for object orientation"""
    try:
        with open(csv_path, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row and abs(float(row[0]) - x) < 0.01 and abs(float(row[1]) - y) < 0.01:
                    # Create a copy of angles from CSV
                    angles = {i+1: int(float(row[i+2])) for i in range(5)}
                    
                    # If object is horizontal, override servo5 angle to 180 degrees
                    if orientation == "horizontal":
                        angles[5] = 180
                    
                    # Move to position
                    print(f"Moving to coordinates ({x}, {y}) with orientation {orientation}")
                    get_move_servos_sequence(ser, angles)
                    return True
        
        print(f"Coordinates ({x}, {y}) not found in saved positions")
        return False
    except ValueError as e:
        print(f"Error with coordinates: {e}")
        return False
    except FileNotFoundError:
        print(f"CSV file not found at: {csv_path}")
        return False

def pick_and_place_object(ser, obj_data):
    """Complete sequence to pick up an object and place it in the appropriate bin"""
    print(f"\nProcessing {obj_data['name']} at coordinates ({obj_data['x']}, {obj_data['y']})")
    
    # Start with arm in parking position and gripper open
    park_servos(ser)
    release_gripper(ser)
    time.sleep(1)
    
    # Move to object position
    success = try_coordinates(ser, obj_data['x'], obj_data['y'], obj_data['orientation'])
    if not success:
        print(f"Failed to move to object position, skipping this object")
        return False
    
    # Grab object
    time.sleep(0.5)
    start_gripping(ser)
    time.sleep(1)
    
    # Move to appropriate bin based on object class
    bin_color = obj_data['bin']
    move_to_bin(ser, bin_color)
    time.sleep(0.5)
    
    # Release object
    release_gripper(ser)
    time.sleep(1)
    
    # Return to parking position
    park_servos(ser)
    time.sleep(0.5)
    
    print(f"Successfully placed {obj_data['name']} in {bin_color} bin")
    return True

def processing_thread(ser, model, cap, scale):
    """Thread for continuous object detection and processing"""
    global processing_active
    
    processing_active = True
    print("Starting automatic object processing...")

    # Update status in the UI
    if app:
        app.update_status("PROCESSING ACTIVE", "green")
    
    while processing_active:
        # Capture frame
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            break
            
        # Detect objects
        detections = detect_objects(frame, model, scale)
        
        if detections:
            print(f"\nFound {len(detections)} objects to sort")
            
            for obj in detections:
                print(f"Processing: {obj['name']} at ({obj['x']}, {obj['y']}), orientation: {obj['orientation']}")
                
                # Update the UI to highlight the object being processed
                if app:
                    app.current_object = obj
                    update_frame_event.set()
                
                pick_and_place_object(ser, obj)
                
                # Clear the current object highlight
                if app:
                    app.current_object = None
                    update_frame_event.set()
                
                # Check if processing has been stopped
                if not processing_active:
                    break
        else:
            print("No objects detected, waiting...")
            time.sleep(1)
    
    print("Automatic processing stopped")
    
    # Update status in the UI
    if app:
        app.update_status("Press 'p' to start processing", "black")

def draw_coordinate_plane(frame, scale, detections=None, current_object=None):
    """Draw coordinate grid, detected objects, and bounding boxes on frame"""
    height, width = frame.shape[:2]
    center_x, center_y = width // 2, height // 2
    unit_pixel = min(width, height) // (4 * scale)
    
    overlay = np.zeros_like(frame)
    
    # Draw grid lines
    for x in range(center_x % unit_pixel, width, unit_pixel):
        cv2.line(overlay, (x, 0), (x, height), (128, 128, 128), 1)
    
    for y in range(center_y % unit_pixel, height, unit_pixel):
        cv2.line(overlay, (0, y), (width, y), (128, 128, 128), 1)
    
    # Draw axes
    cv2.line(overlay, (0, center_y), (width, center_y), (255, 255, 255), 2)
    cv2.line(overlay, (center_x, 0), (center_x, height), (255, 255, 255), 2)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    font_thickness = 1
    
    # Draw coordinate numbers
    for i in range(-2 * scale, 2 * scale + 1):
        x = center_x + i * unit_pixel
        if 0 <= x < width:
            cv2.putText(overlay, str(i), (x - 10, center_y + 20), font, font_scale, (255, 255, 255), font_thickness)
    
    for i in range(-2 * scale, 2 * scale + 1):
        y = center_y - i * unit_pixel
        if 0 <= y < height:
            cv2.putText(overlay, str(i), (center_x + 5, y + 5), font, font_scale, (255, 255, 255), font_thickness)
    
    frame_with_overlay = cv2.addWeighted(frame, 1, overlay, 0.3, 0)
    
    # Draw detected objects
    if detections:
        for obj in detections:
            class_id = obj["class_id"]
            x, y = obj["x"], obj["y"]
            x1, y1, x2, y2 = obj["box"]
            
            # Determine color based on class
            color = CLASS_MAPPING[class_id]["color"]
            
            # Highlight the current object being processed
            thickness = 3
            if current_object and obj["id"] == current_object.get("id"):
                thickness = 5
                # Draw a thicker box for the current object being processed
                cv2.rectangle(frame_with_overlay, (x1, y1), (x2, y2), (0, 255, 255), thickness)
            else:
                # Draw bounding box for each detected object
                cv2.rectangle(frame_with_overlay, (x1, y1), (x2, y2), color, thickness)
            
            # Convert grid coordinates back to pixel
            pixel_x = center_x + x * unit_pixel
            pixel_y = center_y - y * unit_pixel
            
            # Draw circle at object center
            cv2.circle(frame_with_overlay, (pixel_x, pixel_y), 8, color, -1)
            
            # Draw label with confidence
            label = f"{obj['name']} ({x},{y}) {obj['orientation']} {obj['confidence']:.2f}"
            cv2.putText(
                frame_with_overlay, 
                label,
                (x1, y1 - 10), 
                font, font_scale, color, font_thickness
            )
    
    # Add processing status
    status_text = "PROCESSING ACTIVE" if processing_active else "Press 'p' to start processing"
    cv2.putText(
        frame_with_overlay,
        status_text,
        (10, 30),
        font,
        1,
        (0, 255, 255) if processing_active else (255, 255, 255),
        2
    )
    
    return frame_with_overlay

class WasteSortingApp:
    def __init__(self, root, ser):
        self.root = root
        self.root.title("Waste Sorting System Controller")
        self.ser = ser
        self.scale = 1
        self.current_object = None
        
        self.root.configure(bg="#f0f0f0")
        self.root.geometry("1400x900")
        
        # Create frames
        self.control_frame = ttk.Frame(root, padding="10")
        self.control_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.video_frame = ttk.Frame(root)
        self.video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Video display
        self.video_label = ttk.Label(self.video_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Control panels
        self.create_servo_controls()
        self.create_action_controls()
        self.create_status_panel()
        
        # Initialize servo sliders with default values
        self.speed_slider.set(servo_speed)
        self.delay_slider.set(interpolation_delay)
        
        # Apply styles
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 12))
        style.configure('TLabel', font=('Arial', 12))
        style.configure('TFrame', background='#f0f0f0')
        
        # Set global video_label for access from other functions
        global video_label
        video_label = self.video_label
        
        # Set global app reference
        global app
        app = self
    
    def create_servo_controls(self):
        control_panel = ttk.LabelFrame(self.control_frame, text="Servo Controls", padding="10")
        control_panel.pack(fill=tk.X, pady=10)
        
        # Servo speed control
        ttk.Label(control_panel, text="Servo Speed:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.speed_slider = ttk.Scale(
            control_panel, 
            from_=5, 
            to=100, 
            orient=tk.HORIZONTAL, 
            length=200,
            command=self.update_servo_speed
        )
        self.speed_slider.grid(row=0, column=1, pady=5)
        self.speed_value = ttk.Label(control_panel, text="30")
        self.speed_value.grid(row=0, column=2, padx=5)
        
        # Interpolation delay control
        ttk.Label(control_panel, text="Interpolation Delay:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.delay_slider = ttk.Scale(
            control_panel, 
            from_=5, 
            to=50, 
            orient=tk.HORIZONTAL, 
            length=200,
            command=self.update_interpolation_delay
        )
        self.delay_slider.grid(row=1, column=1, pady=5)
        self.delay_value = ttk.Label(control_panel, text="15")
        self.delay_value.grid(row=1, column=2, padx=5)
        
        # Grid scale control
        ttk.Label(control_panel, text="Grid Scale:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.scale_slider = ttk.Scale(
            control_panel, 
            from_=1, 
            to=10, 
            orient=tk.HORIZONTAL, 
            length=200,
            command=self.update_grid_scale
        )
        self.scale_slider.set(self.scale)
        self.scale_slider.grid(row=2, column=1, pady=5)
        self.scale_value = ttk.Label(control_panel, text="1")
        self.scale_value.grid(row=2, column=2, padx=5)
    
    def create_action_controls(self):
        action_panel = ttk.LabelFrame(self.control_frame, text="Actions", padding="10")
        action_panel.pack(fill=tk.X, pady=10)
        
        # Start/stop processing button
        self.process_button = ttk.Button(
            action_panel, 
            text="Start Processing (p)", 
            command=self.toggle_processing
        )
        self.process_button.pack(fill=tk.X, pady=5)
        
        # Park servos button
        ttk.Button(
            action_panel, 
            text="Park Position", 
            command=lambda: park_servos(self.ser)
        ).pack(fill=tk.X, pady=5)
        
        # Open/close gripper buttons
        gripper_frame = ttk.Frame(action_panel)
        gripper_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            gripper_frame, 
            text="Open Gripper", 
            command=lambda: release_gripper(self.ser)
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        ttk.Button(
            gripper_frame, 
            text="Close Gripper", 
            command=lambda: start_gripping(self.ser)
        ).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=2)
        
        # Quit button
        ttk.Button(
            action_panel, 
            text="Quit (q)", 
            command=self.quit_app
        ).pack(fill=tk.X, pady=5)
    
    def create_status_panel(self):
        status_panel = ttk.LabelFrame(self.control_frame, text="Status", padding="10")
        status_panel.pack(fill=tk.X, pady=10)
        
        self.status_label = ttk.Label(
            status_panel, 
            text="Ready", 
            font=('Arial', 14, 'bold')
        )
        self.status_label.pack(pady=5)
        
        # Object info frame
        object_info = ttk.LabelFrame(status_panel, text="Current Object", padding="5")
        object_info.pack(fill=tk.X, pady=5)
        
        self.object_name_label = ttk.Label(object_info, text="None")
        self.object_name_label.pack(fill=tk.X, pady=2)
        
        self.object_pos_label = ttk.Label(object_info, text="Position: -")
        self.object_pos_label.pack(fill=tk.X, pady=2)
        
        self.object_bin_label = ttk.Label(object_info, text="Bin: -")
        self.object_bin_label.pack(fill=tk.X, pady=2)
    
    def update_servo_speed(self, value):
        global servo_speed
        servo_speed = int(float(value))
        self.speed_value.config(text=str(servo_speed))
        set_servo_speed(self.ser, servo_speed)
    
    def update_interpolation_delay(self, value):
        global interpolation_delay
        interpolation_delay = int(float(value))
        self.delay_value.config(text=str(interpolation_delay))
        set_interpolation_delay(self.ser, interpolation_delay)
    
    def update_grid_scale(self, value):
        self.scale = int(float(value))
        self.scale_value.config(text=str(self.scale))
        update_frame_event.set()
    
    def toggle_processing(self):
        global processing_active
        
        if processing_active:
            processing_active = False
            self.process_button.config(text="Start Processing (p)")
            self.update_status("Ready", "black")
        else:
            self.process_button.config(text="Stop Processing (p)")
            self.update_status("Starting...", "orange")
            # Actual processing is started in the key handler
            self.root.event_generate('<KeyPress-p>')
    
    def update_status(self, text, color="black"):
        self.status_label.config(text=text, foreground=color)
        
        # Update object info if there's a current object
        if self.current_object:
            obj = self.current_object
            self.object_name_label.config(text=f"Type: {obj['name']}")
            self.object_pos_label.config(text=f"Position: ({obj['x']}, {obj['y']})")
            self.object_bin_label.config(text=f"Bin: {obj['bin']}")
        else:
            self.object_name_label.config(text="None")
            self.object_pos_label.config(text="Position: -")
            self.object_bin_label.config(text="Bin: -")
    
    def quit_app(self):
        global processing_active
        processing_active = False
        self.root.quit()

def video_stream_thread(cap, model):
    """Thread for updating the video stream in the UI"""
    global processing_active, app, update_frame_event
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            break
        
        # Detect objects
        detections = detect_objects(frame, model, app.scale if app else 1)
        
        # Draw overlay with detections
        frame_with_overlay = draw_coordinate_plane(
            frame, 
            app.scale if app else 1, 
            detections, 
            app.current_object if app else None
        )
        
        # Convert to format suitable for tkinter
        img = cv2.cvtColor(frame_with_overlay, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img = ImageTk.PhotoImage(image=img)
        
        # Update the video label
        if video_label is not None:
            video_label.config(image=img)
            video_label.image = img
        
        # Wait for the update_frame_event or a short timeout
        update_frame_event.wait(timeout=0.03)
        update_frame_event.clear()
        
        # Check if application is closed
        if not cap.isOpened():
            break

def main():
    global processing_active
    
    # Initialize serial connection
    ser = connect_serial()
    if not ser:
        print("Failed to connect to Arduino. Exiting...")
        return
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # Load YOLO model
    model = YOLO('computerVision/bestn.pt')
    
    # Initialize robot
    set_servo_speed(ser, servo_speed)
    set_interpolation_delay(ser, interpolation_delay)
    park_servos(ser)
    release_gripper(ser)
    
    print("Waste sorting system initialized.")
    
    # Create and start tkinter app
    root = tk.Tk()
    app = WasteSortingApp(root, ser)
    
    # Start video stream thread
    video_thread = threading.Thread(target=video_stream_thread, args=(cap, model))
    video_thread.daemon = True
    video_thread.start()
    
    # Processing thread
    process_thread = None
    
    # Key event handler
    def key_handler(event):
        global processing_active
        
        if event.char == 'p':
            if processing_active:
                processing_active = False
                if process_thread:
                    process_thread.join()
                    app.process_button.config(text="Start Processing (p)")
            else:
                # Start new processing thread
                process_thread = threading.Thread(
                    target=processing_thread,
                    args=(ser, model, cap, app.scale)
                )
                process_thread.daemon = True
                process_thread.start()
                app.process_button.config(text="Stop Processing (p)")
        elif event.char == 'q':
            root.quit()
    
    # Bind key events
    root.bind('<KeyPress>', key_handler)
    
    # Main tkinter loop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        # Clean up
        processing_active = False
        if cap.isOpened():
            cap.release()
        if ser:
            ser.close()
            print("Serial connection closed")

if __name__ == "__main__":
    main()