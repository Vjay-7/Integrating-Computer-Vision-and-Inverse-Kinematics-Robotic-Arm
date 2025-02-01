import cv2
import numpy as np


cap = cv2.VideoCapture(0)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)  
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080) 

ret, frame = cap.read()
if not ret:
    print("Error: Could not read frame from webcam.")
    exit()
height, width, _ = frame.shape
print(f"Webcam resolution: {width}x{height}")

center_x = width // 2
center_y = height // 2

# Spacing between grid lines
grid_spacing = 100

def draw_coordinate_plane(frame, center_x, center_y, grid_spacing):
 
    overlay = frame.copy()
    alpha = 0.6  

    
    for x in range(center_x % grid_spacing, width, grid_spacing):
        cv2.line(overlay, (x, 0), (x, height), (255, 255, 255), 1)


    for y in range(center_y % grid_spacing, height, grid_spacing):
        cv2.line(overlay, (0, y), (width, y), (255, 255, 255), 1)

 
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


    cv2.line(frame, (center_x, 0), (center_x, height), (0, 0, 255), 3)  
    cv2.line(frame, (0, center_y), (width, center_y), (0, 255, 0), 3)  
    return frame


cv2.namedWindow('Webcam with Coordinate Plane', cv2.WINDOW_NORMAL)
cv2.resizeWindow('Webcam with Coordinate Plane', 1280, 720) 


display_width = 1280
display_height = 720

while True:

    ret, frame = cap.read()
    if not ret:
        break

    frame = draw_coordinate_plane(frame, center_x, center_y, grid_spacing)

    resized_frame = cv2.resize(frame, (display_width, display_height), interpolation=cv2.INTER_LINEAR)

    cv2.imshow('Webcam with Coordinate Plane', resized_frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('w'):
        center_y = max(0, center_y - 5)
    elif key == ord('s'): 
        center_y = min(height, center_y + 5)
    elif key == ord('a'): 
        center_x = max(0, center_x - 5)
    elif key == ord('d'):  
        center_x = min(width, center_x + 5)

  
    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()