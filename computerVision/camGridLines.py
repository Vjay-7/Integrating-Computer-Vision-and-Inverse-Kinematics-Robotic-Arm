import cv2
import numpy as np

def draw_coordinate_plane(frame, scale):
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
    return cv2.addWeighted(frame, 1, overlay, 0.3, 0)

def main():
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    
    # Try to set a more standard resolution (720p)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    # Get the actual resolution that was set
    actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"Actual resolution: {actual_width}x{actual_height}")
    
    scale = 1  # Initial scale for the coordinate plane
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Draw coordinate plane on frame
        frame_with_plane = draw_coordinate_plane(frame, scale)
        
        # Display the result
        cv2.imshow('Webcam with Coordinate Plane', frame_with_plane)
        
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