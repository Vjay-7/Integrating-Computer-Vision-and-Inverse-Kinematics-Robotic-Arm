import cv2
from ultralytics import YOLO

# Load your trained YOLOv8 model
model = YOLO("yolo11_v6.pt")  # Replace with the path to your model

# Open the webcam
cap = cv2.VideoCapture(0)  # 0 for default webcam, change if you have multiple cameras

if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

while True:
    # Read a frame from the webcam
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to capture image.")
        break

    # Perform object detection on the frame with a confidence threshold of 0.7
    results = model(frame, conf=0.7)

    # Visualize the results on the frame
    annotated_frame = results[0].plot()

    # Display the annotated frame
    cv2.imshow("Trash Detection", annotated_frame)

    # Break the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam and close all OpenCV windows
cap.release()
cv2.destroyAllWindows()
