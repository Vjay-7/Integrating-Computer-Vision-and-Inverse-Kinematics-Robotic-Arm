from ultralytics import YOLO
import cv2

# Load the pretrained trash detection model
# Replace 'trash_detection_model.pt' with the path to your model
model = YOLO('best.pt')

# Set the model to use CPU (if you don't have CUDA)
model.to('cpu')

# Function to detect trash in an image with a confidence threshold
def detect_trash(image_path, confidence_threshold=0.5):
    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        print("Error: Could not load image.")
        return
    
    # Perform inference
    results = model(image)
    
    # Parse the results
    for result in results:
        # Get bounding boxes, confidence scores, and class labels
        boxes = result.boxes.xyxy.cpu().numpy()  # Bounding boxes in [x1, y1, x2, y2] format
        confidences = result.boxes.conf.cpu().numpy()  # Confidence scores
        class_ids = result.boxes.cls.cpu().numpy().astype(int)  # Class IDs
        class_names = result.names  # Class names dictionary
        
        # Loop through all detections
        for box, confidence, class_id in zip(boxes, confidences, class_ids):
            if confidence >= confidence_threshold:  # Filter by confidence threshold
                x1, y1, x2, y2 = map(int, box)  # Convert box coordinates to integers
                label = class_names[class_id]  # Get the class label
                
                # Draw the bounding box
                cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Green box
                
                # Put the label and confidence score on the image
                text = f"{label} {confidence:.2f}"
                cv2.putText(image, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    # Display the annotated image
    cv2.imshow('Trash Detection', image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Example usage
detect_trash('ezgif-frame-024.jpg', confidence_threshold=0.1)