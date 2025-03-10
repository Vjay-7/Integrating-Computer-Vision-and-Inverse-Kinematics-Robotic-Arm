import cv2
import numpy as np
from ultralytics import YOLO

def get_coordinate_from_pixel(pixel_x, pixel_y, center_x, center_y, unit_pixel, scale):
    # Convert pixel coordinates to grid coordinates
    grid_x = round((pixel_x - center_x) / unit_pixel)
    grid_y = round((center_y - pixel_y) / unit_pixel)  # Inverted Y because pixel coordinates go down
    return grid_x, grid_y

def draw_coordinate_plane(frame, scale, detections=None):
    height, width = frame.shape[:2]
    center_x, center_y = width // 2, height // 2
    
    # Create an overlay for the grid and axes
    overlay = np.zeros_like(frame)
    
    # Draw grid lines
    unit_pixel = min(width, height) // (4 * scale)  # Distance between grid lines in pixels
    
    # Vertical grid lines
    for x in range(center_x % unit_pixel, width, unit_pixel):
        cv2.line(overlay, (x, 0), (x, height), (128, 128, 128), 1)
    
    # Horizontal grid lines
    for y in range(center_y % unit_pixel, height, unit_pixel):
        cv2.line(overlay, (0, y), (width, y), (128, 128, 128), 1)
    
    # Draw main axes with bold lines
    # X-axis
    cv2.line(overlay, (0, center_y), (width, center_y), (255, 255, 255), 2)
    # Y-axis
    cv2.line(overlay, (center_x, 0), (center_x, height), (255, 255, 255), 2)
    
    # Add numbers on axes
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    font_thickness = 1
    
    # X-axis numbers
    for i in range(-2 * scale, 2 * scale + 1):
        x = center_x + i * unit_pixel
        if 0 <= x < width:
            cv2.putText(overlay, str(i), 
                       (x - 10, center_y + 20),
                       font, font_scale, (255, 255, 255), font_thickness)
    
    # Y-axis numbers
    for i in range(-2 * scale, 2 * scale + 1):
        y = center_y - i * unit_pixel
        if 0 <= y < height:
            cv2.putText(overlay, str(i),
                       (center_x + 5, y + 5),
                       font, font_scale, (255, 255, 255), font_thickness)
    
    # Blend the overlay with the original frame
    frame_with_overlay = cv2.addWeighted(frame, 1, overlay, 0.3, 0)
    
    # Draw detections if available
    if detections:
        for detection in detections:
            # Get bounding box coordinates
            x1, y1, x2, y2 = detection.boxes.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            
            # Calculate center point
            center_point_x = int((x1 + x2) / 2)
            center_point_y = int((y1 + y2) / 2)
            
            # Get grid coordinates
            grid_x, grid_y = get_coordinate_from_pixel(
                center_point_x, center_point_y, 
                center_x, center_y, 
                unit_pixel, scale
            )
            
            # Get class and choose color
            class_id = int(detection.boxes.cls[0])
            if class_id == 0:  # non-biodegradable
                color = (0, 0, 255)  # Red
                class_name = "Non-biodegradable"
            elif class_id == 1:  # biodegradable
                color = (0, 255, 0)  # Green
                class_name = "Biodegradable"
            else:  # recyclable
                color = (0, 255, 255)  # Yellow
                class_name = "Recyclable"
            
            # Draw bounding box
            cv2.rectangle(frame_with_overlay, (x1, y1), (x2, y2), color, 2)
            
            # Draw center point
            cv2.circle(frame_with_overlay, (center_point_x, center_point_y), 4, color, -1)
            
            # Draw coordinates and class name
            coord_text = f"({grid_x}, {grid_y})"
            cv2.putText(frame_with_overlay, 
                       f"{class_name} {coord_text}", 
                       (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 
                       0.5, 
                       color, 
                       2)
    
    return frame_with_overlay

def main():
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # Get the actual resolution
    actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"Actual resolution: {actual_width}x{actual_height}")
    
    # Load YOLOv8 model
    model = YOLO('bestn.pt')
    
    scale = 1  # Initial scale for the coordinate plane
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Run YOLOv8 inference
        results = model(frame, conf=0.5)  # Adjust confidence threshold as needed
        
        # Draw coordinate plane and detections
        frame_with_plane = draw_coordinate_plane(frame, scale, results[0] if results else None)
        
        # Display the result
        cv2.imshow('Webcam with Coordinate Plane and Detection', frame_with_plane)
        
        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):  # Press 'q' to quit
            break
        elif key == ord('H'):  # Press 'H' to increase scale
            scale = min(scale + 1, 10)
        elif key == ord('h'):  # Press 'h' to decrease scale
            scale = max(scale - 1, 1)
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()