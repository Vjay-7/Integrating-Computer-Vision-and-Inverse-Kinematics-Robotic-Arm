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
BIN_SERVO_SEQUENCE = [1, 2, 3, 4]
GET_SERVO_SEQUENCE = [5, 1, 4, 3, 2, ]
PARK_ANGLES = {
    1: 94,
    2: 77,
    3: 164,
    4: 40,
    5: 90,
}

# Predefined bin positions
BIN_POSITIONS = {
    "blue": {1: 162, 2: 153, 3: 175, 4: 123, 5: 90},    # Biodegradable
    "black": {1: 100, 2: 109, 3: 180, 4: 170, 5: 90},   # Non-biodegradable
    "red": {1: 31, 2: 169, 3: 143, 4: 95, 5: 90}       # Recyclable
}

# Computer vision constants
CLASS_MAPPING = {
    0: {"name": "Recyclable Paper", "bin": "black", "priority": 2, "color": (0, 0, 255)},  # Red
    1: {"name": "Residual", "bin": "blue", "priority": 1, "color": (0, 255, 0)},     # Green
    2: {"name": "Recyclable Bottle", "bin": "red", "priority": 3, "color": (255, 255, 0)}        # Yellow
}

# Global variables
servo_angles = [94, 77, 164, 40, 90, 80]
servo_speed = 30
interpolation_delay = 30
processing_active = False
app = None
video_label = None
update_frame_event = threading.Event()
grid_center_x_offset = -150
grid_center_y_offset = 100
object_list = []
current_attempt_counts = {}
problematic_objects = []
visual_verification_active = True

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
            
def release_gripper_bin(ser):
    send_command(ser, 6, 20)  # 20 degrees for bin release
    print("Gripper released at bin position")

def move_to_bin(ser, bin_color):
    print(f"Moving to {bin_color} bin")
    move_servos_sequence(ser, BIN_POSITIONS[bin_color], BIN_SERVO_SEQUENCE)

def park_servos(ser):
    print("Moving to parking position")
    move_servos_sequence(ser, PARK_ANGLES)
    
# Computer Vision functions
def get_coordinate_from_pixel(pixel_x, pixel_y, center_x, center_y, unit_pixel, scale):
    # Account for the grid center offsets
    grid_x = round((pixel_x - center_x) / unit_pixel)
    grid_y = round((center_y - pixel_y) / unit_pixel)
    return grid_x, grid_y

def detect_objects(frame, model, scale=1):
    height, width = frame.shape[:2]
    # Apply offsets to center coordinates
    center_x = width // 2 + grid_center_x_offset
    center_y = height // 2 + grid_center_y_offset
    unit_pixel = min(width, height) // (4 * scale)
    
    results = model(frame, conf=0.5)
    detections = []
    
    if results and len(results) > 0:
        result = results[0]
        class_counts = {0: 1, 1: 1, 2: 1}  # Track object counts per class
        
        for i, box in enumerate(result.boxes.xyxy):
            x1, y1, x2, y2 = map(int, box)
            
            # Calculate the exact center point of the bounding box
            center_point_x = (x1 + x2) // 2
            center_point_y = (y1 + y2) // 2
            
            # Calculate grid coordinates from pixel coordinates
            grid_x, grid_y = get_coordinate_from_pixel(center_point_x, center_point_y, center_x, center_y, unit_pixel, scale)
            
            obj_width, obj_height = x2 - x1, y2 - y1
            orientation = "horizontal" if obj_width > obj_height * 1.2 else "vertical"
            
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
                    "pixel_center_x": center_point_x,  # Store actual pixel center x
                    "pixel_center_y": center_point_y,  # Store actual pixel center y
                    "orientation": orientation,
                    "box": (x1, y1, x2, y2),  # Store bounding box coordinates
                    "confidence": float(result.boxes.conf[i])
                }
                
                detections.append(detection)
    
    # Sort detections by priority
    detections.sort(key=lambda x: x["confidence"], reverse=True)
    
    return detections

def try_coordinates(ser, x, y, orientation, csv_path='save_angles.csv'):
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
                        angles[5] = 165
                    
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
    
    if app:
        app.current_object = obj_data
        app.update_status(f"Processing: {obj_data['name']}", "green")
        update_frame_event.set()
        
    # Start with arm in parking position and gripper open
    park_servos(ser)
    release_gripper_bin(ser)
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
    time.sleep(3)
    
    # Release object
    release_gripper(ser)
    time.sleep(1.5)
    
    # Return to parking position
    park_servos(ser)
    time.sleep(1)
    
    print(f"Successfully placed {obj_data['name']} in {bin_color} bin")
    # Update the UI again to show which bin the object was placed in
    if app:
        app.update_status(f"Placed {obj_data['name']} in {bin_color} bin", "green")
        update_frame_event.set()
        time.sleep(1)  # Keep the message visible briefly
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
    global grid_center_x_offset, grid_center_y_offset
    height, width = frame.shape[:2]
    # Apply offsets to center coordinates
    center_x = width // 2 + grid_center_x_offset
    center_y = height // 2 + grid_center_y_offset
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
            center_point_x = obj.get("pixel_center_x", (x1 + x2) // 2)
            center_point_y = obj.get("pixel_center_y", (y1 + y2) // 2)
            # Determine color based on class
            color = CLASS_MAPPING[class_id]["color"]
            
            # Highlight the current object being processed
            thickness = 3
            if current_object and obj["id"] == current_object.get("id"):
                thickness = 5
            
            # Draw bounding box
            cv2.rectangle(frame_with_overlay, (x1, y1), (x2, y2), color, thickness)
            
            # Draw circle at the exact center of the bounding box
            cv2.circle(frame_with_overlay, (center_point_x, center_point_y), 8, color, -1)
            
            # Draw label with confidence
            label = f"{obj['name']} ({obj['x']},{obj['y']}) {obj['orientation']} CONF:{obj['confidence']:.2f}"
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


def initial_object_scan(cap, model, scale):
    """Take a baseline image and create a priority-sorted list of all objects detected"""
    global object_list
    
    print("Performing initial object scan...")
    
    # Capture frame
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture initial scan frame")
        return []
    
    # Store a copy of the frame
    frame_copy = frame.copy()
    
    # Detect objects
    detections = detect_objects(frame, model, scale)
    
    # Create a fresh object list with attempt counts
    object_list = []
    for obj in detections:
        obj_id = obj["id"]
        current_attempt_counts[obj_id] = 0
        # Store the frame with each object
        obj["frame"] = frame_copy
        object_list.append(obj)
    
    # Sort by priority
    object_list.sort(key=lambda x: x["confidence"], reverse=True)
    
    print(f"Initial scan complete. Found {len(object_list)} objects to process")
    return object_list

def show_verification_frames(before_frame, after_frame, target_obj):
    """Display before and after frames for visual verification in a separate window"""
    # Calculate the maximum width and height that would fit well on most monitors
    max_display_width = 1200
    max_display_height = 800
    
    # Get original dimensions
    h, w = before_frame.shape[:2]
    
    # Calculate scaling factor to fit within maximum dimensions
    # We'll stack images vertically, so total height will be 2*h
    scale_factor = min(max_display_width / w, max_display_height / (2*h))
    
    # Resize frames if needed
    if scale_factor < 1:
        new_width = int(w * scale_factor)
        new_height = int(h * scale_factor)
        before_frame_resized = cv2.resize(before_frame.copy(), (new_width, new_height))
        after_frame_resized = cv2.resize(after_frame.copy(), (new_width, new_height))
    else:
        before_frame_resized = before_frame.copy()
        after_frame_resized = after_frame.copy()
    
    # Get new dimensions
    h_new, w_new = before_frame_resized.shape[:2]
    
    # Create a stacked image with before on top and after on bottom
    combined = np.zeros((h_new*2, w_new, 3), dtype=np.uint8)
    
    # Add before frame on top
    combined[:h_new, :] = before_frame_resized
    cv2.putText(combined, "BEFORE", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    
    # Add after frame on bottom
    combined[h_new:, :] = after_frame_resized
    cv2.putText(combined, "AFTER", (10, h_new+30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    
    # Calculate scaled position for circles
    center_x = target_obj.get("pixel_center_x", 0)
    center_y = target_obj.get("pixel_center_y", 0)
    
    if scale_factor < 1:
        center_x = int(center_x * scale_factor)
        center_y = int(center_y * scale_factor)
    
    # Draw circles at target object location on both frames
    cv2.circle(combined, (center_x, center_y), 15, (0, 0, 255), 2)  # Circle on before image
    # Drawing a faded circle on the after image at the same x position
    cv2.circle(combined, (center_x, center_y + h_new), 15, (0, 0, 255), 2)
    
    # Add verification status text
    if target_obj.get("verification_success", False):
        status_text = "VERIFICATION SUCCESS: Object removed"
        color = (0, 255, 0)  # Green
    else:
        status_text = "VERIFICATION FAILED: Object still present"
        color = (0, 0, 255)  # Red
    
    cv2.putText(combined, status_text, (10, 2*h_new-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    
    # Show the combined image
    cv2.namedWindow("Verification Frames", cv2.WINDOW_NORMAL)
    cv2.imshow("Verification Frames", combined)
    cv2.resizeWindow("Verification Frames", w_new, h_new*2)
    cv2.waitKey(1)  # Update the window

def visual_verification(cap, model, scale, target_obj):
    """Check if the object was successfully picked up by comparing before/after images"""
    print(f"Performing visual verification for {target_obj['name']}...")
    
    # Store the "before" frame (from object_list creation)
    before_frame = target_obj.get("frame", None)
    
    # Capture "after" frame
    ret, after_frame = cap.read()
    if not ret:
        print("Failed to capture verification frame")
        return False
    
    # Detect objects in new frame
    current_detections = detect_objects(after_frame, model, scale)
    
    # Get target object properties for comparison
    target_id = target_obj["id"]
    target_class = target_obj["class_id"]
    target_x, target_y = target_obj["x"], target_obj["y"]
    
    # Define adjacent cells to check (original position + up, down, left, right)
    check_positions = [
        (target_x, target_y),  # Original position
        (target_x, target_y + 1),  # Up
        (target_x, target_y - 1),  # Down
        (target_x + 1, target_y),  # Right
        (target_x - 1, target_y)   # Left
    ]
    
    # Assume success until proven otherwise
    success = True
    
    # Check if the target object is still present at original or adjacent positions
    for obj in current_detections:
        # Only check objects of the same class
        if obj["class_id"] == target_class:
            # Check if object is at original or adjacent coordinates
            if (obj["x"], obj["y"]) in check_positions:
                position_found = (obj["x"], obj["y"])
                print(f"Verification FAILED: {target_obj['name']} still detected at position {position_found}")
                success = False
                break
    
    # Store verification result in the object for later reference
    target_obj["verification_success"] = success
    
    # Display the verification frames if both frames are available
    if before_frame is not None and after_frame is not None:
        show_verification_frames(before_frame, after_frame, target_obj)
    
    if success:
        print(f"Verification SUCCESS: {target_obj['name']} successfully removed from ({target_x}, {target_y})")
    
    return success

def disarrangement_strategy(ser, obj):
    """Perform a gentle push to disarrange an object that's difficult to pick up"""
    print(f"Executing disarrangement strategy for {obj['name']} at ({obj['x']}, {obj['y']})")
    
    # Open gripper
    release_gripper(ser)
    time.sleep(0.5)
    
    # Move to object position
    try_coordinates(ser, obj['x'], obj['y'], obj['orientation'])
    time.sleep(0.5)
    
    # Get current servo1 angle for later movements
    current_servo1_angle = servo_angles[0]  # Servo 1 (0-indexed)
    
    # Rotate servo5 to 180 degrees
    send_command(ser, 5, 180)
    time.sleep(0.5)
    
    # Rotate servo5 back to 90 degrees
    send_command(ser, 5, 90)
    time.sleep(0.5)
    
    # Move servo1 +30 degrees from current position
    new_angle_plus = min(current_servo1_angle + 20, 180)  # Ensure we don't exceed servo limits
    send_command(ser, 1, new_angle_plus)
    time.sleep(0.5)
    
    # Move servo1 -60 degrees from the current position (meaning -30 from original position)
    new_angle_minus = max(current_servo1_angle - 20, 0) 
    send_command(ser, 1, new_angle_minus)
    time.sleep(0.5)
    
    # Return servo1 to original position
    send_command(ser, 1, current_servo1_angle)
    time.sleep(0.5)
    
    # Return to parking position
    park_servos(ser)
    
    print("Disarrangement strategy complete")
    
    
def process_object_with_verification(ser, obj, cap, model, scale):
    """Complete sequence to pick up an object with visual verification"""
    obj_id = obj['id']
    print(f"\nAttempting to process {obj['name']} at ({obj['x']}, {obj['y']})")
    
    if app:
        app.current_object = obj
        app.update_status(f"Processing: {obj['name']}", "green")
        update_frame_event.set()
    
    # Start with arm in parking position and gripper open
    park_servos(ser)
    release_gripper_bin(ser)
    time.sleep(1)
    
    # Move to object position
    success = try_coordinates(ser, obj['x'], obj['y'], obj['orientation'])
    if not success:
        print(f"Failed to move to object position")
        return False
    
    # Grab object
    time.sleep(0.5)
    start_gripping(ser)
    time.sleep(1)
    
    # Move to parking position with object
    park_servos(ser)
    time.sleep(1)
    
    # Verify if pickup was successful
    if visual_verification_active:
        pickup_success = visual_verification(cap, model, scale, obj)
    else:
        pickup_success = True  # Assume success if verification is disabled
    
    if pickup_success:
        # Move to appropriate bin based on object class
        bin_color = obj['bin']
        move_to_bin(ser, bin_color)
        time.sleep(1)
        
        # Release object
        release_gripper(ser)
        time.sleep(1)
        
        # Return to parking position
        park_servos(ser)
        
        print(f"Successfully placed {obj['name']} in {bin_color} bin")
        
        if app:
            app.update_status(f"Placed {obj['name']} in {bin_color} bin", "green")
            update_frame_event.set()
        
        # Remove object from the list
        return True
    else:
        # Release the object and return to parking
        release_gripper(ser)
        park_servos(ser)
        
        # Update attempt count
        current_attempt_counts[obj_id] = current_attempt_counts.get(obj_id, 0) + 1
        
        if app:
            app.update_status(f"Failed to pick up {obj['name']}", "red")
            update_frame_event.set()
        
        return False
    

def enhanced_processing_thread(ser, model, cap, scale):
    """Thread for continuous object detection and processing with verification and retry logic"""
    global processing_active, object_list, current_attempt_counts, problematic_objects
    
    processing_active = True
    print("Starting enhanced automatic object processing...")

    # Update status in the UI
    if app:
        app.update_status("PROCESSING ACTIVE", "green")
    
    # Initial scan to populate object list
    object_list = initial_object_scan(cap, model, scale)
    
    while processing_active:
        # Process all objects in the list
        while object_list and processing_active:
            # Select highest priority object
            obj = object_list[0]
            obj_id = obj["id"]
            
            # Process the object with verification
            success = process_object_with_verification(ser, obj, cap, model, scale)
            
            if success:
                # Remove from list on success
                object_list.remove(obj)
                current_attempt_counts[obj_id] = 0
            else:
                # Handle failure based on attempt count
                attempts = current_attempt_counts[obj_id]
                
                if attempts >= 2:
                    # Execute disarrangement strategy
                    disarrangement_strategy(ser, obj)
                    
                    # Reset attempt counter
                    current_attempt_counts[obj_id] = 0
                    
                    # Rescan to update positions
                    object_list = initial_object_scan(cap, model, scale)
                else:
                    # Move object to end of list for retry later
                    object_list.remove(obj)
                    object_list.append(obj)
        
        # If all objects processed or processing stopped, check for new objects
        if processing_active:
            print("Completed current object list. Scanning for new objects...")
            object_list = initial_object_scan(cap, model, scale)
            
            # If no new objects, wait and try again
            if not object_list:
                print("No objects detected, waiting...")
                time.sleep(2)
                object_list = initial_object_scan(cap, model, scale)
    
    print("Enhanced automatic processing stopped")
    
    # Update status in the UI
    if app:
        app.update_status("Press 'p' to start processing", "black")
        


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
    
    def update_grid_y_position(self, value):
        global grid_center_y_offset
        grid_center_y_offset = int(float(value))
        self.grid_y_value.config(text=str(grid_center_y_offset))
        update_frame_event.set()

    def update_grid_x_position(self, value):
        global grid_center_x_offset
        grid_center_x_offset = int(float(value))
        self.grid_x_value.config(text=str(grid_center_x_offset))
        update_frame_event.set()
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
        
        # Grid position controls
        ttk.Label(control_panel, text="Grid Vertical Position:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.grid_y_slider = ttk.Scale(
            control_panel, 
            from_=-100, 
            to=100, 
            orient=tk.HORIZONTAL, 
            length=200,
            command=self.update_grid_y_position
        )
        self.grid_y_slider.set(grid_center_y_offset)
        self.grid_y_slider.grid(row=3, column=1, pady=5)
        self.grid_y_value = ttk.Label(control_panel, text="0")
        self.grid_y_value.grid(row=3, column=2, padx=5)

        ttk.Label(control_panel, text="Grid Horizontal Position:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.grid_x_slider = ttk.Scale(
            control_panel, 
            from_=-200,  # Changed from -100 to -150
            to=100, 
            orient=tk.HORIZONTAL, 
            length=200,
            command=self.update_grid_x_position
        )
        self.grid_x_slider.set(grid_center_x_offset)
        self.grid_x_slider.grid(row=4, column=1, pady=5)
        self.grid_x_value = ttk.Label(control_panel, text="0")
        self.grid_x_value.grid(row=4, column=2, padx=5)
    
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
        
            # Add verification toggle
        verification_frame = ttk.Frame(status_panel)
        verification_frame.pack(fill=tk.X, pady=5)
        
        self.verification_var = tk.BooleanVar(value=True)
        verification_check = ttk.Checkbutton(
            verification_frame,
            text="Enable Visual Verification",
            variable=self.verification_var,
            command=self.toggle_verification
        )
        verification_check.pack(side=tk.LEFT)
        
        
    def toggle_verification(self):
        global visual_verification_active
        visual_verification_active = self.verification_var.get()
        print(f"Visual verification {'enabled' if visual_verification_active else 'disabled'}")
    
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
    model = YOLO('computerVision/yolov12-100v6.pt')
    
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
                # Start new processing thread with enhanced version
                process_thread = threading.Thread(
                    target=enhanced_processing_thread,
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