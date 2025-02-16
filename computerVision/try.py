import cv2

# Open the webcam (0 for default camera)
cap = cv2.VideoCapture(0)

# Get the width and height of the webcam frame
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

print(f"Webcam Resolution: {width}x{height}")

# Release the webcam
cap.release()
cv2.destroyAllWindows()
