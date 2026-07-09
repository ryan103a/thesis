import argparse
import cv2
import numpy as np

def main():
    # 1. Set up command line argument parsing
    parser = argparse.ArgumentParser(
        description="Extract the first frame of a video."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        help="Path to the input video file (e.g., video.avi)",
    )
    args = parser.parse_args()

    # 2. Open the video file using the argument
    cap = cv2.VideoCapture(args.input)

    if not cap.isOpened():
        print(f"Error: Could not open the video file at {args.input}")
        return

    TARGET_FRAME_INDEX = 120
    cap.set(cv2.CAP_PROP_POS_FRAMES, TARGET_FRAME_INDEX)

    # 3. Read the first frame
    success, frame = cap.read()

    if success:
        # 4. Save the frame
        output_image_path = "first_frame.png"
        # cv2.imwrite(output_image_path, frame)

        cv2.imshow(output_image_path, frame)
        cv2.waitKey(0)

        print(f"Successfully saved the first frame to {output_image_path}")
    else:
        print("Error: Could not read the first frame.")

    # Checkerboard detection

    # 1. Define the internal corner dimensions (cols, rows)
    # For a grid of 10x7 squares, internal corners are 9x6
    PATTERN_SIZE = (8, 5)

    # 2. Load the image and convert it to grayscale
    # image = cv2.imread('checkerboard.jpg')
    image = frame
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    THRESHOLD = 200
    _, gray = cv2.threshold(gray, THRESHOLD, 255, cv2.THRESH_BINARY)

    # Define a 3x3 sharpening kernel
    # The elements must sum to 1 to preserve overall image brightness
    kernel = np.array([[-1, -1, -1], 
                       [-1, 9, -1], 
                       [-1, -1, -1]])

    # Apply the kernel to the image
    # -1 ensures the output image matches the depth of the input image
    gray = cv2.filter2D(gray, -1, kernel)

    cv2.imshow('Grayscale image', gray)
    cv2.waitKey(0)

    # 3. Detect the corners using the Sector-Based (SB) method
    # This method automatically handles subpixel localization and produces highly accurate points.
    found, corners = cv2.findChessboardCornersSB(gray, PATTERN_SIZE, None)

    # 4. If found, draw the corners and display the result
    if found:
        print(f"Success! Detected all {PATTERN_SIZE[0] * PATTERN_SIZE[1]} inner corners.")
        
        # Draw the corner points and connecting lines onto the original image
        cv2.drawChessboardCorners(gray, PATTERN_SIZE, corners, found)
        
        # Display to screen
        cv2.imshow("Detected Checkerboard Corners (SB Method)", gray)
        print("Press any key on the image window to close.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("Failed to detect the checkerboard pattern.")

    # 5. Clean up resources
    cap.release()


if __name__ == "__main__":
    main()

