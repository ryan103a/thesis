import cv2
import numpy as np
from pathlib import Path

# Define internal corner grid size (columns, rows)
# Always count the number of internal intersection points, NOT the squares!
CHECKERBOARD = (9, 6) 

# Load image and convert to grayscale
image = cv2.imread('checkerboard.jpeg')

if image is None:
    print("image not foudn")

cv2.imshow('image', image)
cv2.waitKey(0)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Find the chess board corners
# For enhanced accuracy in tough lighting, you can substitute this function with:
# cv2.findChessboardCornersSB() (Symmetry-Based)
ret, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)

if ret:
    # Subpixel refinement for pixel-perfect tracking
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
    corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
    
    # Draw corners onto the original image
    cv2.drawChessboardCorners(image, CHECKERBOARD, corners_refined, ret)
    
    # Display the result
    cv2.imshow('Detected Checkerboard', image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
else:
    print("Checkerboard pattern could not be found.")

