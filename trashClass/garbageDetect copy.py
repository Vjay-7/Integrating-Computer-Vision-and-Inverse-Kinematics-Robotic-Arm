import cv2
import torch
from ultralytics import YOLO

# Load the YOLOv8 model
model = YOLO('D:/ThesisV.1/Integrating-Computer-Vision-and-Inverse-Kinematics-Robotic-Arm/trashClass/runs/detect/train/weights/best.pt')  # Adjust the path to your model's weights

# Define class colors
class_colors = {
    'Biodegradable': (0, 255, 0),  # Green
    'Recyclable': (255, 0, 0),     # Blue
    'Residual': (0, 0, 255)        # Red
}

# Initialize the camera
cap = cv2.VideoCapture(0)  # Use 0 for the default camera

# Initialize variables to store frame dimensions
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Define Cartesian plane parameters based on frame dimensions
plane_center = (frame_width // 2, frame_height // 2)  # Center of the Cartesian plane
scale_factor = 20  # Scale factor for displaying coordinates
unit_interval = 50  # Interval between units on the x and y axes

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Flip the frame vertically and horizontally
    frame = cv2.flip(frame, 1)

    # Perform detection
    results = model(frame)

    # Draw Cartesian plane
    cv2.line(frame, (0, plane_center[1]), (frame_width, plane_center[1]), (255, 255, 255), 1)  # X-axis
    cv2.line(frame, (plane_center[0], 0), (plane_center[0], frame_height), (255, 255, 255), 1)  # Y-axis

    # Draw the intervals on the x-axis
    for x in range(plane_center[0], frame_width, unit_interval):
        cv2.line(frame, (x, plane_center[1] - 5), (x, plane_center[1] + 5), (255, 255, 255), 1)
        cv2.putText(frame, f'{(x-plane_center[0])//scale_factor}', (x, plane_center[1] + 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    for x in range(plane_center[0], 0, -unit_interval):
        cv2.line(frame, (x, plane_center[1] - 5), (x, plane_center[1] + 5), (255, 255, 255), 1)
        cv2.putText(frame, f'{(x-plane_center[0])//scale_factor}', (x, plane_center[1] + 20), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Draw the intervals on the y-axis
    for y in range(plane_center[1], frame_height, unit_interval):
        cv2.line(frame, (plane_center[0] - 5, y), (plane_center[0] + 5, y), (255, 255, 255), 1)
        cv2.putText(frame, f'{(plane_center[1]-y)//scale_factor}', (plane_center[0] + 10, y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    for y in range(plane_center[1], 0, -unit_interval):
        cv2.line(frame, (plane_center[0] - 5, y), (plane_center[0] + 5, y), (255, 255, 255), 1)
        cv2.putText(frame, f'{(plane_center[1]-y)//scale_factor}', (plane_center[0] + 10, y), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Process the results
    for result in results:
        boxes = result.boxes
        for box in boxes:
            # Extract the bounding box coordinates, confidence score, and class id
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = box.conf[0]
            cls = int(box.cls[0])
            class_name = model.names[cls]

            # Get the color for the class
            color = class_colors.get(class_name, (0, 255, 255))  # Default to yellow if class not found

            # Draw the bounding box
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)

            # Draw the center point
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            cv2.circle(frame, (center_x, center_y), 5, color, -1)

            # Calculate Cartesian coordinates relative to the center of the screen
            cartesian_x = (center_x - plane_center[0]) // scale_factor
            cartesian_y = (plane_center[1] - center_y) // scale_factor  # Invert y-axis for Cartesian coordinates

            # Display the coordinates near the detected object
            text_position = (int(center_x) + 10, int(center_y) - 10)
            cv2.putText(frame, f"({cartesian_x}, {cartesian_y})", text_position,
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # Display the frame with detections
    cv2.imshow('YOLOv8 Detection', frame)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the camera and close all windows
cap.release()
cv2.destroyAllWindows()
