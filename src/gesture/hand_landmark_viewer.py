"""
Hand Landmark Viewer — Displays MediaPipe hand landmarks on the robot camera stream.

This module connects to the DJI Robomaster EP Core camera via STA mode,
runs MediaPipe Hands on each frame, and draws the 21 hand landmarks
with connections in real time.

Usage:
    python -m src.gesture.hand_landmark_viewer
"""

import sys
import os

import cv2
import mediapipe as mp
from robomaster import robot, camera

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.robot_config import CONN_TYPE

# MediaPipe drawing utilities
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles


def run_hand_landmark_viewer():
    """Connect to the robot camera and display hand landmarks in real time."""

    # Initialize robot connection
    ep_robot = robot.Robot()
    ep_robot.initialize(conn_type=CONN_TYPE)
    print("[OK] Robot connected via '{}'.".format(CONN_TYPE))

    ep_camera = ep_robot.camera
    ep_camera.start_video_stream(display=False, resolution=camera.STREAM_720P)
    print("[OK] Camera stream started.")

    # Initialize MediaPipe Hands
    # max_num_hands: maximum number of hands to detect
    # min_detection_confidence: minimum confidence for initial detection
    # min_tracking_confidence: minimum confidence for tracking between frames
    hands = mp_hands.Hands(
        max_num_hands=3,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
    )

    print("[OK] MediaPipe Hands initialized.")
    print("Press 'q' to quit.")

    try:
        while True:
            # Read frame from robot camera
            img = ep_camera.read_cv2_image(strategy="newest", timeout=0.5)

            # Convert BGR (OpenCV) to RGB (MediaPipe expects RGB)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Process frame with MediaPipe Hands
            results = hands.process(img_rgb)

            # Draw landmarks if hands are detected
            if results.multi_hand_landmarks:
                for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    # Draw the 21 landmarks and connections on the frame
                    mp_drawing.draw_landmarks(
                        img,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style(),
                    )

                    # Determine if it is a left or right hand
                    handedness = results.multi_handedness[hand_idx].classification[0]
                    label = handedness.label
                    confidence = handedness.score

                    # Display hand label at the wrist position (landmark 0)
                    wrist = hand_landmarks.landmark[0]
                    h, w, _ = img.shape
                    cx, cy = int(wrist.x * w), int(wrist.y * h)
                    cv2.putText(
                        img,
                        "{} ({:.0f}%)".format(label, confidence * 100),
                        (cx, cy - 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (255, 255, 255),
                        2,
                    )

            cv2.imshow("Hand Landmark Viewer", img)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        hands.close()
        cv2.destroyAllWindows()
        ep_camera.stop_video_stream()
        ep_robot.close()
        print("[OK] Cleanup complete.")


if __name__ == "__main__":
    run_hand_landmark_viewer()
