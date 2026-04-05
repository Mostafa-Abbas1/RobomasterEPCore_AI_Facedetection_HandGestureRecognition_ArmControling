"""
Gesture Controller — Connects gesture recognition to robot commands.

Reads the robot camera stream, classifies hand gestures via MediaPipe
and GestureClassifier, and sends the corresponding commands to the robot.

Gesture-to-command mapping:
    STOP          → Robot stops all movement
    FORWARD       → Robot drives forward slowly
    ARM_UP        → Robotic arm moves up
    ARM_DOWN      → Robotic arm moves down
    GRIPPER_OPEN  → Gripper opens
    GRIPPER_CLOSE → Gripper closes

Usage:
    python -m src.gesture.gesture_controller
"""

import sys
import os
import time

import cv2
import mediapipe as mp
from robomaster import robot, camera, led

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.robot_config import CONN_TYPE
from src.gesture.gesture_classifier import (
    GestureClassifier,
    GESTURE_STOP,
    GESTURE_FORWARD,
    GESTURE_ARM_UP,
    GESTURE_ARM_DOWN,
    GESTURE_GRIPPER_OPEN,
    GESTURE_GRIPPER_CLOSE,
    GESTURE_NONE,
)

# MediaPipe drawing utilities
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Robot movement speeds (intentionally slow for safety)
CHASSIS_SPEED = 0.05         # m/s forward speed (very slow)
ARM_STEP = 20                # mm per command cycle
GRIPPER_POWER = 30           # gripper motor power (0-100)

# Minimum time between consecutive robot commands (seconds)
COMMAND_COOLDOWN = 0.5

# Number of consecutive identical detections required before executing a command.
# This prevents flickering between gestures from triggering unwanted commands.
GESTURE_STABILITY_THRESHOLD = 5

# LED colors for each gesture (r, g, b)
GESTURE_LED_COLORS = {
    GESTURE_STOP:          (255, 0,   0),    # Red
    GESTURE_FORWARD:       (0,   255, 0),    # Green
    GESTURE_ARM_UP:        (0,   0,   255),  # Blue
    GESTURE_ARM_DOWN:      (0,   255, 255),  # Cyan
    GESTURE_GRIPPER_OPEN:  (255, 255, 0),    # Yellow
    GESTURE_GRIPPER_CLOSE: (255, 0,   255),  # Magenta
    GESTURE_NONE:          (0,   0,   0),    # Off
}


def run_gesture_controller():
    """Main loop: camera stream → gesture recognition → robot commands."""

    # Connect to robot
    ep_robot = robot.Robot()
    ep_robot.initialize(conn_type=CONN_TYPE)
    print("[OK] Robot connected via '{}'.".format(CONN_TYPE))

    ep_camera = ep_robot.camera
    ep_chassis = ep_robot.chassis
    ep_arm = ep_robot.robotic_arm
    ep_gripper = ep_robot.gripper
    ep_led = ep_robot.led

    ep_camera.start_video_stream(display=False, resolution=camera.STREAM_720P)
    print("[OK] Camera stream started.")

    # Initialize MediaPipe Hands
    hands = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
    )

    classifier = GestureClassifier()
    last_command_time = 0
    last_gesture = GESTURE_NONE
    is_moving = False
    gesture_counter = 0          # Counts consecutive identical detections
    pending_gesture = GESTURE_NONE  # The gesture being accumulated

    print("[OK] Gesture controller ready.")
    print("Gestures: 5_FINGERS=stop, 3_FINGERS=forward, 1_FINGER=arm_up,")
    print("          2_FINGERS=arm_down, 4_FINGERS(no thumb)=gripper_open,")
    print("          FIST=gripper_close")
    print("Press 'q' to quit.")

    try:
        while True:
            # Read frame with error handling to prevent crash on timeout
            try:
                img = ep_camera.read_cv2_image(strategy="newest", timeout=1.0)
            except Exception:
                continue

            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = hands.process(img_rgb)

            current_gesture = GESTURE_NONE

            if results.multi_hand_landmarks:
                for hand_idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    # Draw landmarks on the frame
                    mp_drawing.draw_landmarks(
                        img,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style(),
                    )

                    # Classify gesture
                    handedness = results.multi_handedness[hand_idx].classification[0]
                    current_gesture = classifier.classify(
                        hand_landmarks, handedness.label
                    )

            # Gesture stabilization: only act after N consecutive identical detections
            if current_gesture == pending_gesture:
                gesture_counter += 1
            else:
                pending_gesture = current_gesture
                gesture_counter = 1

            stable_gesture = pending_gesture if gesture_counter >= GESTURE_STABILITY_THRESHOLD else None

            # Display gesture name and stability status on screen
            color = (0, 255, 0) if stable_gesture and stable_gesture != GESTURE_NONE else (0, 0, 255)
            display_text = "Gesture: {}".format(pending_gesture)
            if stable_gesture is None:
                display_text += " (stabilizing...)"
            cv2.putText(
                img,
                display_text,
                (10, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                color,
                2,
            )

            # Execute robot command only for stable gestures
            now = time.time()
            if stable_gesture and now - last_command_time >= COMMAND_COOLDOWN:
                if stable_gesture != last_gesture or stable_gesture == GESTURE_FORWARD:
                    _execute_command(
                        stable_gesture,
                        ep_chassis, ep_arm, ep_gripper, ep_led,
                        is_moving,
                    )
                    if stable_gesture == GESTURE_FORWARD:
                        is_moving = True
                    elif stable_gesture == GESTURE_STOP:
                        is_moving = False

                    last_gesture = stable_gesture
                    last_command_time = now

            # If no hand detected and robot was moving, stop it
            if not results.multi_hand_landmarks and is_moving:
                if now - last_command_time >= COMMAND_COOLDOWN:
                    print("[CMD] No hand detected → STOP")
                    ep_chassis.drive_speed(x=0, y=0, z=0)
                    ep_led.set_led(comp=led.COMP_ALL, r=255, g=0, b=0, effect=led.EFFECT_ON)
                    is_moving = False
                    last_gesture = GESTURE_NONE
                    last_command_time = now

            cv2.imshow("Gesture Controller", img)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        # Safety: stop all movement on exit
        ep_chassis.drive_speed(x=0, y=0, z=0)
        ep_led.set_led(comp=led.COMP_ALL, r=0, g=0, b=0, effect=led.EFFECT_ON)
        hands.close()
        cv2.destroyAllWindows()
        ep_camera.stop_video_stream()
        ep_robot.close()
        print("[OK] Gesture controller stopped.")


def _execute_command(gesture, ep_chassis, ep_arm, ep_gripper, ep_led, is_moving):
    """
    Send the appropriate robot command for the given gesture.

    Args:
        gesture: Gesture name constant from gesture_classifier.
        ep_chassis: Robot chassis module.
        ep_arm: Robot arm module.
        ep_gripper: Robot gripper module.
        ep_led: Robot LED module.
        is_moving: Whether the robot is currently moving forward.
    """
    # Set LED color for the detected gesture
    r, g, b = GESTURE_LED_COLORS.get(gesture, (0, 0, 0))
    ep_led.set_led(comp=led.COMP_ALL, r=r, g=g, b=b, effect=led.EFFECT_ON)

    # Stop ongoing actions before executing the new command
    ep_chassis.drive_speed(x=0, y=0, z=0)
    ep_gripper.pause()

    if gesture == GESTURE_STOP:
        print("[CMD] STOP")

    elif gesture == GESTURE_FORWARD:
        print("[CMD] FORWARD (speed={} m/s)".format(CHASSIS_SPEED))
        ep_chassis.drive_speed(x=CHASSIS_SPEED, y=0, z=0)

    elif gesture == GESTURE_ARM_UP:
        print("[CMD] ARM UP ({}mm)".format(ARM_STEP))
        ep_arm.move(x=0, y=ARM_STEP).wait_for_completed()

    elif gesture == GESTURE_ARM_DOWN:
        print("[CMD] ARM DOWN ({}mm)".format(ARM_STEP))
        ep_arm.move(x=0, y=-ARM_STEP).wait_for_completed()

    elif gesture == GESTURE_GRIPPER_OPEN:
        # Gripper runs continuously until a different gesture is detected
        print("[CMD] GRIPPER OPEN (continuous)")
        ep_gripper.open(power=GRIPPER_POWER)

    elif gesture == GESTURE_GRIPPER_CLOSE:
        # Gripper runs continuously until a different gesture is detected
        print("[CMD] GRIPPER CLOSE (continuous)")
        ep_gripper.close(power=GRIPPER_POWER)


if __name__ == "__main__":
    run_gesture_controller()
