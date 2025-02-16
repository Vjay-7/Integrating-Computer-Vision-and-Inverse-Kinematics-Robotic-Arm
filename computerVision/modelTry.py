import cv2
from ultralytics import YOLO  


model = YOLO("bestm.pt")


image_path = "image2.jpg"
results = model.predict(image_path)

result = results[0]
result_image = result.plot()


max_size = 800
height, width = result_image.shape[:2]
if width > height:
    new_width = max_size
    new_height = int(height * (max_size / width))
else:
    new_height = max_size
    new_width = int(width * (max_size / height))

resized_image = cv2.resize(result_image, (new_width, new_height))


cv2.imshow('Detection Result', resized_image)
cv2.waitKey(0)  
cv2.destroyAllWindows()  