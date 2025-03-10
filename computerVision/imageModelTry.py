import cv2
from ultralytics import YOLO  

# Load YOLOv8 model
model = YOLO("bestn150.pt")

# Load and predict on image
image_path = "ezgif-frame-024.jpg"
results = model.predict(image_path)

# Get the first result
result = results[0]

# Extract bounding boxes and determine orientation
for box in result.boxes:
    x, y, w, h = box.xywh[0]  # Get bounding box (center x, center y, width, height)
    class_id = int(box.cls[0])  # Class ID
    confidence = box.conf[0].item()  # Confidence score

    # Determine orientation
    orientation = "Horizontal" if w > h else "Vertical"

    print(f"Class: {class_id}, Confidence: {confidence:.2f}, Orientation: {orientation}")

# Draw detections
result_image = result.plot()

# Resize image for display
max_size = 800
height, width = result_image.shape[:2]
if width > height:
    new_width = max_size
    new_height = int(height * (max_size / width))
else:
    new_height = max_size
    new_width = int(width * (max_size / height))

resized_image = cv2.resize(result_image, (new_width, new_height))

# Display image
cv2.imshow('Detection Result', resized_image)
cv2.waitKey(0)  
cv2.destroyAllWindows()
