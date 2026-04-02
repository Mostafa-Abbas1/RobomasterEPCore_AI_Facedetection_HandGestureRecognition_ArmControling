"""
Individual test functions for DJI Robomaster EP Core.

Each test can be run independently to verify a specific robot subsystem.
Usage:
    python -m tests.test_robot_connection --test connection
    python -m tests.test_robot_connection --test battery
    python -m tests.test_robot_connection --test chassis
    python -m tests.test_robot_connection --test camera
    python -m tests.test_robot_connection --test arm
    python -m tests.test_robot_connection --test gripper
    python -m tests.test_robot_connection --test led
    python -m tests.test_robot_connection --test vision_person
    python -m tests.test_robot_connection --test vision_gesture
"""

import sys
import os
import time
import argparse
import threading

import cv2
from robomaster import robot, led, camera

# Add project root to path for config import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.robot_config import CONN_TYPE


def connect_robot():
    """Initialize and return a connected robot instance."""
    ep_robot = robot.Robot()
    ep_robot.initialize(conn_type=CONN_TYPE)
    print("[OK] Robot connected via '{}'.".format(CONN_TYPE))
    return ep_robot


def disconnect_robot(ep_robot):
    """Safely close the robot connection."""
    ep_robot.close()
    print("[OK] Robot connection closed.")


# ---------------------------------------------------------------------------
# Test 1: Connection & Firmware Version
# ---------------------------------------------------------------------------
def test_connection():
    """Test basic connection and retrieve the robot firmware version."""
    ep_robot = connect_robot()
    try:
        version = ep_robot.get_version()
        print("[OK] Firmware version: {}".format(version))
    finally:
        disconnect_robot(ep_robot)


# ---------------------------------------------------------------------------
# Test 2: Battery Level
# ---------------------------------------------------------------------------
def test_battery():
    """Query the current battery percentage."""
    ep_robot = connect_robot()
    try:
        battery_level = []

        def battery_callback(info):
            battery_level.append(info)
            print("[OK] Battery level: {}%".format(info))

        ep_battery = ep_robot.battery
        ep_battery.sub_battery_info(freq=5, callback=battery_callback)
        # Wait for one callback to arrive
        time.sleep(3)
        ep_battery.unsub_battery_info()

        if not battery_level:
            print("[WARN] No battery info received.")
    finally:
        disconnect_robot(ep_robot)


# ---------------------------------------------------------------------------
# Test 3: Chassis Movement
# ---------------------------------------------------------------------------
def test_chassis():
    """Test chassis movement: forward, backward, left, right, rotate."""
    ep_robot = connect_robot()
    try:
        ep_chassis = ep_robot.chassis
        speed = 0.5
        distance = 0.3
        rotation = 45

        print("Moving forward {}m...".format(distance))
        ep_chassis.move(x=distance, y=0, z=0, xy_speed=speed).wait_for_completed()
        print("[OK] Forward done.")

        print("Moving backward {}m...".format(distance))
        ep_chassis.move(x=-distance, y=0, z=0, xy_speed=speed).wait_for_completed()
        print("[OK] Backward done.")

        print("Moving left {}m...".format(distance))
        ep_chassis.move(x=0, y=-distance, z=0, xy_speed=speed).wait_for_completed()
        print("[OK] Left done.")

        print("Moving right {}m...".format(distance))
        ep_chassis.move(x=0, y=distance, z=0, xy_speed=speed).wait_for_completed()
        print("[OK] Right done.")

        print("Rotating left {}°...".format(rotation))
        ep_chassis.move(x=0, y=0, z=rotation, z_speed=45).wait_for_completed()
        print("[OK] Rotate left done.")

        print("Rotating right {}°...".format(rotation))
        ep_chassis.move(x=0, y=0, z=-rotation, z_speed=45).wait_for_completed()
        print("[OK] Rotate right done.")
    finally:
        disconnect_robot(ep_robot)


# ---------------------------------------------------------------------------
# Test 4: Camera Video Stream
# ---------------------------------------------------------------------------
def test_camera():
    """Start the video stream and display 100 frames in an OpenCV window."""
    ep_robot = connect_robot()
    try:
        ep_camera = ep_robot.camera
        ep_camera.start_video_stream(display=False, resolution=camera.STREAM_720P)
        print("[OK] Video stream started. Displaying 100 frames (press 'q' to quit)...")

        for i in range(100):
            img = ep_camera.read_cv2_image(strategy="newest", timeout=0.5)
            cv2.imshow("Camera Test", img)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()
        ep_camera.stop_video_stream()
        print("[OK] Video stream stopped.")
    finally:
        disconnect_robot(ep_robot)


# ---------------------------------------------------------------------------
# Test 5: Robotic Arm
# ---------------------------------------------------------------------------
def test_arm():
    """Test robotic arm movement: forward, backward, up, down."""
    ep_robot = connect_robot()
    try:
        ep_arm = ep_robot.robotic_arm
        step = 20  # millimeters

        print("Arm moving forward {}mm...".format(step))
        ep_arm.move(x=step, y=0).wait_for_completed()
        print("[OK] Arm forward done.")

        print("Arm moving backward {}mm...".format(step))
        ep_arm.move(x=-step, y=0).wait_for_completed()
        print("[OK] Arm backward done.")

        print("Arm moving up {}mm...".format(step))
        ep_arm.move(x=0, y=step).wait_for_completed()
        print("[OK] Arm up done.")

        print("Arm moving down {}mm...".format(step))
        ep_arm.move(x=0, y=-step).wait_for_completed()
        print("[OK] Arm down done.")
    finally:
        disconnect_robot(ep_robot)


# ---------------------------------------------------------------------------
# Test 6: Gripper
# ---------------------------------------------------------------------------
def test_gripper():
    """Test gripper open and close actions."""
    ep_robot = connect_robot()
    try:
        ep_gripper = ep_robot.gripper

        print("Opening gripper...")
        ep_gripper.open(power=50)
        time.sleep(1)
        ep_gripper.pause()
        print("[OK] Gripper opened.")

        print("Closing gripper...")
        ep_gripper.close(power=50)
        time.sleep(1)
        ep_gripper.pause()
        print("[OK] Gripper closed.")
    finally:
        disconnect_robot(ep_robot)


# ---------------------------------------------------------------------------
# Test 7: LED
# ---------------------------------------------------------------------------
def test_led():
    """Cycle through red, green, blue on all LEDs."""
    ep_robot = connect_robot()
    try:
        ep_led = ep_robot.led
        colors = [
            ("Red",   255, 0,   0),
            ("Green", 0,   255, 0),
            ("Blue",  0,   0,   255),
        ]

        for name, r, g, b in colors:
            print("Setting LEDs to {}...".format(name))
            ep_led.set_led(comp=led.COMP_ALL, r=r, g=g, b=b, effect=led.EFFECT_ON)
            time.sleep(1)
            print("[OK] {} done.".format(name))

        # Turn off LEDs
        ep_led.set_led(comp=led.COMP_ALL, r=0, g=0, b=0, effect=led.EFFECT_ON)
        print("[OK] LEDs turned off.")
    finally:
        disconnect_robot(ep_robot)


# ---------------------------------------------------------------------------
# Test 8: Built-in Vision — Person Detection
# ---------------------------------------------------------------------------
def test_vision_person():
    """Test the robot's built-in person detection with camera overlay."""
    ep_robot = connect_robot()
    try:
        ep_vision = ep_robot.vision
        ep_camera = ep_robot.camera
        persons = []
        lock = threading.Lock()

        def on_detect_person(person_info):
            with lock:
                persons.clear()
                for x, y, w, h in person_info:
                    persons.append((x, y, w, h))
                    print("  Person detected: x={:.2f} y={:.2f} w={:.2f} h={:.2f}".format(x, y, w, h))

        ep_camera.start_video_stream(display=False, resolution=camera.STREAM_720P)
        ep_vision.sub_detect_info(name="person", callback=on_detect_person)
        print("[OK] Person detection started. Displaying 200 frames (press 'q' to quit)...")

        for i in range(200):
            img = ep_camera.read_cv2_image(strategy="newest", timeout=0.5)
            with lock:
                for x, y, w, h in persons:
                    pt1 = (int((x - w / 2) * 1280), int((y - h / 2) * 720))
                    pt2 = (int((x + w / 2) * 1280), int((y + h / 2) * 720))
                    cv2.rectangle(img, pt1, pt2, (0, 255, 0), 2)
            cv2.imshow("Person Detection", img)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()
        ep_vision.unsub_detect_info(name="person")
        ep_camera.stop_video_stream()
        print("[OK] Person detection stopped.")
    finally:
        disconnect_robot(ep_robot)


# ---------------------------------------------------------------------------
# Test 9: Built-in Vision — Gesture Detection
# ---------------------------------------------------------------------------
def test_vision_gesture():
    """Test the robot's built-in gesture detection with camera overlay."""
    ep_robot = connect_robot()
    try:
        ep_vision = ep_robot.vision
        ep_camera = ep_robot.camera
        gestures = []
        lock = threading.Lock()

        def on_detect_gesture(gesture_info):
            with lock:
                gestures.clear()
                for x, y, w, h, info in gesture_info:
                    gestures.append((x, y, w, h, info))
                    print("  Gesture detected: type={} x={:.2f} y={:.2f}".format(info, x, y))

        ep_camera.start_video_stream(display=False, resolution=camera.STREAM_720P)
        ep_vision.sub_detect_info(name="gesture", callback=on_detect_gesture)
        print("[OK] Gesture detection started. Displaying 200 frames (press 'q' to quit)...")

        for i in range(200):
            img = ep_camera.read_cv2_image(strategy="newest", timeout=0.5)
            with lock:
                for x, y, w, h, info in gestures:
                    pt1 = (int((x - w / 2) * 1280), int((y - h / 2) * 720))
                    pt2 = (int((x + w / 2) * 1280), int((y + h / 2) * 720))
                    cv2.rectangle(img, pt1, pt2, (0, 255, 0), 2)
                    cv2.putText(img, str(info), (pt1[0], pt1[1] - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            cv2.imshow("Gesture Detection", img)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()
        ep_vision.unsub_detect_info(name="gesture")
        ep_camera.stop_video_stream()
        print("[OK] Gesture detection stopped.")
    finally:
        disconnect_robot(ep_robot)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
AVAILABLE_TESTS = {
    "connection":     test_connection,
    "battery":        test_battery,
    "chassis":        test_chassis,
    "camera":         test_camera,
    "arm":            test_arm,
    "gripper":        test_gripper,
    "led":            test_led,
    "vision_person":  test_vision_person,
    "vision_gesture": test_vision_gesture,
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test individual robot subsystems.")
    parser.add_argument(
        "--test",
        choices=list(AVAILABLE_TESTS.keys()),
        required=True,
        help="Name of the subsystem to test.",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("Running test: {}".format(args.test))
    print("=" * 50)
    AVAILABLE_TESTS[args.test]()
    print("=" * 50)
    print("Test '{}' completed.".format(args.test))
    print("=" * 50)
