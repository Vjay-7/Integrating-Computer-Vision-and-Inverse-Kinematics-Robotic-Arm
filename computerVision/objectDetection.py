import cv2
import numpy as np
from ultralytics import YOLO
import math

class CoordinateDetector:
    def __init__(self, model_path='bestm.pt', camera_width=1920, camera_height=1080):
        self.model = YOLO(model_path)
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_height)
        
        # Colors for different classes (BGR format)
        self.colors = {
            'biodegradable': (0, 255, 0),    # Green
            'recyclable': (0, 255, 255),     # Yellow
            'non-biodegradable': (0, 0, 255) # Red
        }
        
        # Coordinate system parameters
        self.x_scale = 50  # pixels per unit on x-axis
        self.y_scale = 50  # pixels per unit on y-axis
        self.scale_step = 10  # pixels to adjust when scaling
        
    def draw_coordinate_system(self, frame):
        height, width = frame.shape[:2]
        center_x, center_y = width // 2, height // 2
        
        # Draw main axes
        cv2.line(frame, (0, center_y), (width, center_y), (255, 255, 255), 1)  # X-axis
        cv2.line(frame, (center_x, 0), (center_x, height), (255, 255, 255), 1)  # Y-axis
        
        # Draw coordinate numbers and tick marks
        for x in range(-10, 11):  # Adjust range based on screen size
            pos_x = center_x + x * self.x_scale
            if 0 <= pos_x < width:
                cv2.line(frame, (pos_x, center_y-5), (pos_x, center_y+5), (255, 255, 255), 1)
                if x != 0:  # Don't draw 0 at center
                    cv2.putText(frame, str(x), (pos_x-10, center_y+20),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        for y in range(-10, 11):  # Adjust range based on screen size
            pos_y = center_y - y * self.y_scale
            if 0 <= pos_y < height:
                cv2.line(frame, (center_x-5, pos_y), (center_x+5, pos_y), (255, 255, 255), 1)
                if y != 0:  # Don't draw 0 at center
                    cv2.putText(frame, str(y), (center_x+10, pos_y+5),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def get_coordinates(self, x, y):
        height, width = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT), self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        center_x, center_y = width // 2, height // 2
        
        coord_x = round((x - center_x) / self.x_scale, 1)
        coord_y = round((center_y - y) / self.y_scale, 1)
        return coord_x, coord_y
    
    def run(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            # Draw coordinate system
            self.draw_coordinate_system(frame)
            
            # Run YOLOv8 detection
            results = self.model(frame, stream=True)
            
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Calculate center point of detection
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    
                    # Get class name
                    cls = int(box.cls[0])
                    class_name = self.model.names[cls]
                    
                    # Get color based on class
                    color = self.colors.get(class_name, (255, 255, 255))
                    
                    # Draw bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Draw center point
                    cv2.circle(frame, (center_x, center_y), 4, color, -1)
                    
                    # Get and display coordinates
                    coord_x, coord_y = self.get_coordinates(center_x, center_y)
                    coord_text = f"{class_name} ({coord_x}, {coord_y})"
                    cv2.putText(frame, coord_text, (x1, y1-10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Display the frame
            # cv2.namedWindow('YOLOv8 Detection', cv2.WINDOW_NORMAL)
            # cv2.setWindowProperty('YOLOv8 Detection', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            # cv2.imshow('YOLOv8 Detection', frame)
            
           
            cv2.namedWindow("Trash Classification", cv2.WINDOW_NORMAL)  
            cv2.resizeWindow("Trash Classification", 960, 540)  # Set width and height
            cv2.imshow("Trash Classification", frame)
            
            # Handle key events
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('X'):
                self.x_scale += self.scale_step
            elif key == ord('x'):
                self.x_scale = max(10, self.x_scale - self.scale_step)
            elif key == ord('Y'):
                self.y_scale += self.scale_step
            elif key == ord('y'):
                self.y_scale = max(10, self.y_scale - self.scale_step)
        
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    detector = CoordinateDetector()
    detector.run()