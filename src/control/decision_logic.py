"""
Decision Logic — Central controller that switches between tracking and gesture mode.

Manages two operating modes:
    TRACKING MODE (default):
        - Robot follows the closest person using YOLO + DeepSORT.
        - Hand gestures are IGNORED.
        - Toggle: Both fists detected → switch to GESTURE MODE.

    GESTURE MODE:
        - Robot responds to single-hand gestures.
        - Person tracking is PAUSED (target ID preserved).
        - Toggle: Both fists detected → switch back to TRACKING MODE
          (continues following the same person).

The dual-fist toggle requires both hands showing a closed fist simultaneously.
This is an unambiguous gesture that won't happen accidentally.

Usage:
    python -m src.control.decision_logic
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
from src.tracking.person_detector import PersonDetector
from src.tracking.person_tracker import PersonTracker
from src.tracking.follow_controller import FollowController

# MediaPipe drawing utilities
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles

# Operating modes
MODE_TRACKING = "TRACKING"
MODE_GESTURE = "GESTURE"

# Gesture mode robot speeds (same as gesture_controller.py)
CHASSIS_SPEED = 0.05
ARM_STEP = 20
GRIPPER_POWER = 30

# Timing
COMMAND_COOLDOWN = 0.5
GESTURE_STABILITY_THRESHOLD = 5

# Number of consecutive frames both fists must be detected to toggle mode.
# Prevents accidental toggles.
TOGGLE_THRESHOLD = 10

# Cooldown after a mode switch to prevent immediate re-toggle (seconds)
TOGGLE_COOLDOWN = 2.0

# LED colors for mode indication
MODE_LED_COLORS = {
    MODE_TRACKING: (0, 0, 255),    # Blue = tracking
    MODE_GESTURE:  (255, 165, 0),  # Orange = gesture
}

# Gesture LED colors (reused from gesture_controller)
GESTURE_LED_COLORS = {
    GESTURE_STOP:          (255, 0,   0),
    GESTURE_FORWARD:       (0,   255, 0),
    GESTURE_ARM_UP:        (0,   0,   255),
    GESTURE_ARM_DOWN:      (0,   255, 255),
    GESTURE_GRIPPER_OPEN:  (255, 255, 0),
    GESTURE_GRIPPER_CLOSE: (255, 0,   255),
    GESTURE_NONE:          (0,   0,   0),
}


def _detect_dual_fist(hand_results, classifier):
    """
    Check if both hands are showing a closed fist.

    Args:
        hand_results: MediaPipe Hands processing result.
        classifier: GestureClassifier instance.

    Returns:
        True if exactly 2 hands are detected and both are classified
        as GRIPPER_CLOSE (fist).
    """
    if not hand_results.multi_hand_landmarks:
        return False
    if len(hand_results.multi_hand_landmarks) != 2:
        return False

    for hand_idx, hand_landmarks in enumerate(hand_results.multi_hand_landmarks):
        handedness = hand_results.multi_handedness[hand_idx].classification[0]
        gesture = classifier.classify(hand_landmarks, handedness.label)
        if gesture != GESTURE_GRIPPER_CLOSE:
            return False

    return True


def _execute_gesture_command(gesture, ep_chassis, ep_arm, ep_gripper, ep_led):
    """Send the robot command corresponding to the recognized gesture."""
    r, g, b = GESTURE_LED_COLORS.get(gesture, (0, 0, 0))
    ep_led.set_led(comp=led.COMP_ALL, r=r, g=g, b=b, effect=led.EFFECT_ON)

    # Stop ongoing actions before executing the new command
    ep_chassis.drive_speed(x=0, y=0, z=0)
    ep_gripper.pause()

    if gesture == GESTURE_STOP:
        print("[GESTURE] STOP")

    elif gesture == GESTURE_FORWARD:
        print("[GESTURE] FORWARD")
        ep_chassis.drive_speed(x=CHASSIS_SPEED, y=0, z=0)

    elif gesture == GESTURE_ARM_UP:
        print("[GESTURE] ARM UP")
        ep_arm.move(x=0, y=ARM_STEP).wait_for_completed()

    elif gesture == GESTURE_ARM_DOWN:
        print("[GESTURE] ARM DOWN")
        ep_arm.move(x=0, y=-ARM_STEP).wait_for_completed()

    elif gesture == GESTURE_GRIPPER_OPEN:
        print("[GESTURE] GRIPPER OPEN")
        ep_gripper.open(power=GRIPPER_POWER)

    elif gesture == GESTURE_GRIPPER_CLOSE:
        print("[GESTURE] GRIPPER CLOSE")
        ep_gripper.close(power=GRIPPER_POWER)


def _draw_tracking_overlay(img, tracks, target_track):
    """Draw bounding boxes and IDs on the frame for all tracked persons."""
    for track in tracks:
        if not track.is_confirmed():
            continue
        left, top, right, bottom = [int(v) for v in track.to_ltrb()]
        track_id = track.track_id

        is_target = target_track and track_id == target_track.track_id
        color = (0, 255, 0) if is_target else (128, 128, 128)
        thickness = 2 if is_target else 1
        label = "FOLLOW ID:{}".format(track_id) if is_target else "ID:{}".format(track_id)

        cv2.rectangle(img, (left, top), (right, bottom), color, thickness)
        cv2.putText(img, label, (left, top - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


def run():
    """Main loop: manages mode switching between tracking and gesture control."""

    # --- Initialize robot ---
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

    # --- Initialize modules ---
    # MediaPipe Hands with 2 hands for dual-fist toggle detection
    hands = mp_hands.Hands(
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
    )
    classifier = GestureClassifier()
    detector = PersonDetector()
    tracker = PersonTracker()
    follower = FollowController()

    # --- State ---
    current_mode = MODE_TRACKING
    toggle_counter = 0
    last_toggle_time = 0
    last_command_time = 0
    last_gesture = GESTURE_NONE
    gesture_counter = 0
    pending_gesture = GESTURE_NONE

    # Set initial LED color
    r, g, b = MODE_LED_COLORS[current_mode]
    ep_led.set_led(comp=led.COMP_ALL, r=r, g=g, b=b, effect=led.EFFECT_ON)

    print("[OK] System ready. Starting in TRACKING mode.")
    print("Show BOTH FISTS to toggle between TRACKING and GESTURE mode.")
    print("Press 'q' to quit.")

    try:
        while True:
            # --- Read frame ---
            try:
                img = ep_camera.read_cv2_image(strategy="newest", timeout=1.0)
            except Exception:
                continue

            now = time.time()

            # --- Hand detection (always active for toggle check) ---
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            hand_results = hands.process(img_rgb)

            # --- Check for dual-fist toggle ---
            if _detect_dual_fist(hand_results, classifier):
                toggle_counter += 1
            else:
                toggle_counter = 0

            if toggle_counter >= TOGGLE_THRESHOLD and now - last_toggle_time >= TOGGLE_COOLDOWN:
                # Switch mode
                if current_mode == MODE_TRACKING:
                    current_mode = MODE_GESTURE
                    # Stop robot movement when entering gesture mode
                    ep_chassis.drive_speed(x=0, y=0, z=0)
                    ep_gripper.pause()
                    last_gesture = GESTURE_NONE
                    gesture_counter = 0
                    pending_gesture = GESTURE_NONE
                else:
                    current_mode = MODE_TRACKING

                toggle_counter = 0
                last_toggle_time = now
                r, g, b = MODE_LED_COLORS[current_mode]
                ep_led.set_led(comp=led.COMP_ALL, r=r, g=g, b=b, effect=led.EFFECT_ON)
                print("[MODE] Switched to {} mode.".format(current_mode))

            # --- Mode-specific processing ---
            if current_mode == MODE_TRACKING:
                # Run person detection and tracking
                detections = detector.detect(img)
                tracks = tracker.update(detections, img)
                target = tracker.get_target()

                _draw_tracking_overlay(img, tracks, target)

                if target:
                    follow_info = follower.follow(target, img.shape, ep_chassis)
                    cv2.putText(
                        img,
                        "Following ID:{} | dist:{:.2f} offset:{:.2f}".format(
                            target.track_id,
                            follow_info["box_ratio"],
                            follow_info["center_offset"],
                        ),
                        (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2,
                    )
                else:
                    follower.stop(ep_chassis)
                    cv2.putText(img, "No person detected — waiting...",
                                (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            elif current_mode == MODE_GESTURE:
                # Draw hand landmarks
                current_gesture = GESTURE_NONE
                if hand_results.multi_hand_landmarks:
                    # Use only the first detected hand for gesture commands
                    hand_landmarks = hand_results.multi_hand_landmarks[0]
                    handedness = hand_results.multi_handedness[0].classification[0]

                    mp_drawing.draw_landmarks(
                        img, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                        mp_drawing_styles.get_default_hand_landmarks_style(),
                        mp_drawing_styles.get_default_hand_connections_style(),
                    )
                    current_gesture = classifier.classify(hand_landmarks, handedness.label)

                # Gesture stabilization
                if current_gesture == pending_gesture:
                    gesture_counter += 1
                else:
                    pending_gesture = current_gesture
                    gesture_counter = 1

                stable_gesture = pending_gesture if gesture_counter >= GESTURE_STABILITY_THRESHOLD else None

                # Execute command for stable gesture
                if stable_gesture and now - last_command_time >= COMMAND_COOLDOWN:
                    if stable_gesture != last_gesture or stable_gesture == GESTURE_FORWARD:
                        _execute_gesture_command(
                            stable_gesture, ep_chassis, ep_arm, ep_gripper, ep_led,
                        )
                        last_gesture = stable_gesture
                        last_command_time = now

                # If no hand detected, stop
                if not hand_results.multi_hand_landmarks:
                    if now - last_command_time >= COMMAND_COOLDOWN:
                        ep_chassis.drive_speed(x=0, y=0, z=0)
                        ep_gripper.pause()
                        last_gesture = GESTURE_NONE
                        last_command_time = now

            # --- Display mode and toggle status on screen ---
            mode_color = (0, 255, 0) if current_mode == MODE_TRACKING else (0, 165, 255)
            cv2.putText(img, "Mode: {}".format(current_mode),
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, mode_color, 2)

            if current_mode == MODE_GESTURE:
                display_text = "Gesture: {}".format(pending_gesture)
                if gesture_counter < GESTURE_STABILITY_THRESHOLD:
                    display_text += " (stabilizing...)"
                cv2.putText(img, display_text,
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            if toggle_counter > 0:
                progress = min(toggle_counter / TOGGLE_THRESHOLD, 1.0)
                cv2.putText(
                    img,
                    "Toggle: {:.0f}%".format(progress * 100),
                    (img.shape[1] - 200, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2,
                )

            cv2.imshow("Robomaster Controller", img)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    finally:
        ep_chassis.drive_speed(x=0, y=0, z=0)
        ep_gripper.pause()
        ep_led.set_led(comp=led.COMP_ALL, r=0, g=0, b=0, effect=led.EFFECT_ON)
        hands.close()
        cv2.destroyAllWindows()
        ep_camera.stop_video_stream()
        ep_robot.close()
        print("[OK] System stopped.")


if __name__ == "__main__":
    run()
