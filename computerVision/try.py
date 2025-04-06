import cv2
import numpy as np
from ultralytics import YOLO

def get_coordinate_from_pixel(pixel_x, pixel_y, center_x, center_y, unit_pixel, scale):
    grid_x = round((pixel_x - center_x) / unit_pixel)
    grid_y = round((center_y - pixel_y) / unit_pixel)
    return grid_x, grid_y

def draw_coordinate_plane(frame, scale, detections=None):
    height, width = frame.shape[:2]
    center_x, center_y = width // 2, height // 2
    overlay = np.zeros_like(frame)
    unit_pixel = min(width, height) // (4 * scale)
    
    for x in range(center_x % unit_pixel, width, unit_pixel):
        cv2.line(overlay, (x, 0), (x, height), (128, 128, 128), 1)
    
    for y in range(center_y % unit_pixel, height, unit_pixel):
        cv2.line(overlay, (0, y), (width, y), (128, 128, 128), 1)
    
    cv2.line(overlay, (0, center_y), (width, center_y), (255, 255, 255), 2)
    cv2.line(overlay, (center_x, 0), (center_x, height), (255, 255, 255), 2)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    font_thickness = 1
    
    for i in range(-2 * scale, 2 * scale + 1):
        x = center_x + i * unit_pixel
        if 0 <= x < width:
            cv2.putText(overlay, str(i), (x - 10, center_y + 20), font, font_scale, (255, 255, 255), font_thickness)
    
    for i in range(-2 * scale, 2 * scale + 1):
        y = center_y - i * unit_pixel
        if 0 <= y < height:
            cv2.putText(overlay, str(i), (center_x + 5, y + 5), font, font_scale, (255, 255, 255), font_thickness)
    
    frame_with_overlay = cv2.addWeighted(frame, 1, overlay, 0.3, 0)
    
    detected_objects = []
    
    if detections:
        class_counts = {0: 1, 1: 1, 2: 1}  # Track object counts per class
        
        for detection in sorted(detections, key=lambda d: d.boxes.cls[0]):
            x1, y1, x2, y2 = map(int, detection.boxes.xyxy[0])
            center_point_x = (x1 + x2) // 2
            center_point_y = (y1 + y2) // 2
            grid_x, grid_y = get_coordinate_from_pixel(center_point_x, center_point_y, center_x, center_y, unit_pixel, scale)
            
            width, height = x2 - x1, y2 - y1
            orientation = "horizontal" if width > height else "vertical"
            
            class_id = int(detection.boxes.cls[0])
            if class_id == 0:
                color = (0, 0, 255)
                class_name = "Non-biodegradable"
            elif class_id == 1:
                color = (0, 255, 0)
                class_name = "Biodegradable"
            else:
                color = (0, 255, 255)
                class_name = "Recyclable"
            
            obj_id = f"{class_name.lower().replace('-', '_')}_{class_counts[class_id]}"
            class_counts[class_id] += 1
            
            detected_objects.append(f"{obj_id} ({grid_x}, {grid_y}) {orientation}")
            
            cv2.rectangle(frame_with_overlay, (x1, y1), (x2, y2), color, 2)
            cv2.circle(frame_with_overlay, (center_point_x, center_point_y), 4, color, -1)
            
            cv2.putText(frame_with_overlay, f"{class_name} {grid_x}, {grid_y} {orientation}", (x1, y1 - 10),
                        font, font_scale, color, font_thickness)
    
    return frame_with_overlay, detected_objects

def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    model = YOLO('bestn.pt')
    scale = 1  
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        results = model(frame, conf=0.5)  
        frame_with_plane, detected_objects = draw_coordinate_plane(frame, scale, results[0] if results else None)
        
        print("Detected Objects:")
        for obj in detected_objects:
            print(obj)
        
        cv2.imshow('Webcam with Coordinate Plane and Detection', frame_with_plane)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('H'):
            scale = min(scale + 1, 10)
        elif key == ord('h'):
            scale = max(scale - 1, 1)
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()