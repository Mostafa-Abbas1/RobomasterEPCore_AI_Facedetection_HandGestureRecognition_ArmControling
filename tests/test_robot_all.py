"""
Run all robot subsystem tests in sequence with a single command.

This script connects once and tests every subsystem one after another.
Usage:
    python -m tests.test_robot_all
"""

import sys
import os
import time
import threading

import cv2
from robomaster import robot, led, camera

# Add project root to path for config import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.robot_config import CONN_TYPE

# Shared state for vision callbacks
_vision_lock = threading.Lock()


def run_all_tests():
    """Connect to the robot once and run every subsystem test sequentially."""

    print("=" * 60)
    print("ROBOMASTER EP CORE — FULL SYSTEM TEST")
    print("=" * 60)

    ep_robot = robot.Robot()
    ep_robot.initialize(conn_type=CONN_TYPE)
    print("[OK] Robot connected via '{}'.\n".format(CONN_TYPE))

    results = {}

    try:
        # --- Test 1: Connection & Version ---
        results["connection"] = _test_connection(ep_robot)

        # --- Test 2: Battery ---
        results["battery"] = _test_battery(ep_robot)

        # --- Test 3: LED ---
        results["led"] = _test_led(ep_robot)

        # --- Test 4: Chassis ---
        results["chassis"] = _test_chassis(ep_robot)

        # --- Test 5: Robotic Arm ---
        results["arm"] = _test_arm(ep_robot)

        # --- Test 6: Gripper ---
        results["gripper"] = _test_gripper(ep_robot)

        # --- Test 7: Camera ---
        results["camera"] = _test_camera(ep_robot)

        # --- Test 8: Built-in Person Detection ---
        results["vision_person"] = _test_vision_person(ep_robot)

        # --- Test 9: Built-in Gesture Detection ---
        results["vision_gesture"] = _test_vision_gesture(ep_robot)

    finally:
        ep_robot.close()
        print("\n[OK] Robot connection closed.")

    # Print summary
    _print_summary(results)


# ---------------------------------------------------------------------------
# Individual test functions (all receive an already-connected robot instance)
# ---------------------------------------------------------------------------

def _test_connection(ep_robot):
    """Verify connection by reading the firmware version."""
    print("-" * 40)
    print("TEST: Connection & Firmware Version")
    print("-" * 40)
    try:
        version = ep_robot.get_version()
        print("[OK] Firmware version: {}".format(version))
        return "PASS"
    except Exception as e:
        print("[FAIL] {}".format(e))
        return "FAIL"


def _test_battery(ep_robot):
    """Read the battery level."""
    print("\n" + "-" * 40)
    print("TEST: Battery")
    print("-" * 40)
    try:
        battery_level = []

        def callback(info):
            battery_level.append(info)

        ep_robot.battery.sub_battery_info(freq=5, callback=callback)
        time.sleep(3)
        ep_robot.battery.unsub_battery_info()

        if battery_level:
            print("[OK] Battery level: {}%".format(battery_level[-1]))
            return "PASS"
        else:
            print("[WARN] No battery info received.")
            return "WARN"
    except Exception as e:
        print("[FAIL] {}".format(e))
        return "FAIL"


def _test_led(ep_robot):
    """Cycle LEDs through red, green, blue."""
    print("\n" + "-" * 40)
    print("TEST: LED")
    print("-" * 40)
    try:
        ep_led = ep_robot.led
        for name, r, g, b in [("Red", 255, 0, 0), ("Green", 0, 255, 0), ("Blue", 0, 0, 255)]:
            ep_led.set_led(comp=led.COMP_ALL, r=r, g=g, b=b, effect=led.EFFECT_ON)
            print("  {} set.".format(name))
            time.sleep(0.8)

        ep_led.set_led(comp=led.COMP_ALL, r=0, g=0, b=0, effect=led.EFFECT_ON)
        print("[OK] LED test done.")
        return "PASS"
    except Exception as e:
        print("[FAIL] {}".format(e))
        return "FAIL"


def _test_chassis(ep_robot):
    """Move chassis forward and backward."""
    print("\n" + "-" * 40)
    print("TEST: Chassis Movement")
    print("-" * 40)
    try:
        ep_chassis = ep_robot.chassis

        print("  Moving forward 0.3m...")
        ep_chassis.move(x=0.3, y=0, z=0, xy_speed=0.5).wait_for_completed()

        print("  Moving backward 0.3m...")
        ep_chassis.move(x=-0.3, y=0, z=0, xy_speed=0.5).wait_for_completed()

        print("  Rotating left 45°...")
        ep_chassis.move(x=0, y=0, z=45, z_speed=45).wait_for_completed()

        print("  Rotating right 45°...")
        ep_chassis.move(x=0, y=0, z=-45, z_speed=45).wait_for_completed()

        print("[OK] Chassis test done.")
        return "PASS"
    except Exception as e:
        print("[FAIL] {}".format(e))
        return "FAIL"


def _test_arm(ep_robot):
    """Move robotic arm in all directions."""
    print("\n" + "-" * 40)
    print("TEST: Robotic Arm")
    print("-" * 40)
    try:
        ep_arm = ep_robot.robotic_arm
        step = 20  # mm

        print("  Arm forward {}mm...".format(step))
        ep_arm.move(x=step, y=0).wait_for_completed()

        print("  Arm backward {}mm...".format(step))
        ep_arm.move(x=-step, y=0).wait_for_completed()

        print("  Arm up {}mm...".format(step))
        ep_arm.move(x=0, y=step).wait_for_completed()

        print("  Arm down {}mm...".format(step))
        ep_arm.move(x=0, y=-step).wait_for_completed()

        print("[OK] Arm test done.")
        return "PASS"
    except Exception as e:
        print("[FAIL] {}".format(e))
        return "FAIL"


def _test_gripper(ep_robot):
    """Open and close the gripper."""
    print("\n" + "-" * 40)
    print("TEST: Gripper")
    print("-" * 40)
    try:
        ep_gripper = ep_robot.gripper

        print("  Opening gripper...")
        ep_gripper.open(power=50)
        time.sleep(1)
        ep_gripper.pause()

        print("  Closing gripper...")
        ep_gripper.close(power=50)
        time.sleep(1)
        ep_gripper.pause()

        print("[OK] Gripper test done.")
        return "PASS"
    except Exception as e:
        print("[FAIL] {}".format(e))
        return "FAIL"


def _test_camera(ep_robot):
    """Open video stream and display 50 frames."""
    print("\n" + "-" * 40)
    print("TEST: Camera Stream")
    print("-" * 40)
    try:
        ep_camera = ep_robot.camera
        ep_camera.start_video_stream(display=False, resolution=camera.STREAM_720P)
        print("  Displaying 50 frames (press 'q' to skip)...")

        for i in range(50):
            img = ep_camera.read_cv2_image(strategy="newest", timeout=0.5)
            cv2.imshow("Camera Test", img)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()
        ep_camera.stop_video_stream()
        print("[OK] Camera test done.")
        return "PASS"
    except Exception as e:
        print("[FAIL] {}".format(e))
        return "FAIL"


def _test_vision_person(ep_robot):
    """Test built-in person detection with camera overlay."""
    print("\n" + "-" * 40)
    print("TEST: Built-in Person Detection")
    print("-" * 40)
    try:
        ep_vision = ep_robot.vision
        ep_camera = ep_robot.camera
        persons = []

        def on_detect(person_info):
            with _vision_lock:
                persons.clear()
                for x, y, w, h in person_info:
                    persons.append((x, y, w, h))

        ep_camera.start_video_stream(display=False, resolution=camera.STREAM_720P)
        ep_vision.sub_detect_info(name="person", callback=on_detect)
        print("  Displaying 100 frames (press 'q' to skip)...")

        detected_count = 0
        for i in range(100):
            img = ep_camera.read_cv2_image(strategy="newest", timeout=0.5)
            with _vision_lock:
                for x, y, w, h in persons:
                    pt1 = (int((x - w / 2) * 1280), int((y - h / 2) * 720))
                    pt2 = (int((x + w / 2) * 1280), int((y + h / 2) * 720))
                    cv2.rectangle(img, pt1, pt2, (0, 255, 0), 2)
                    detected_count += 1
            cv2.imshow("Person Detection", img)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()
        ep_vision.unsub_detect_info(name="person")
        ep_camera.stop_video_stream()
        print("[OK] Person detection done. Detections: {}".format(detected_count))
        return "PASS"
    except Exception as e:
        print("[FAIL] {}".format(e))
        return "FAIL"


def _test_vision_gesture(ep_robot):
    """Test built-in gesture detection with camera overlay."""
    print("\n" + "-" * 40)
    print("TEST: Built-in Gesture Detection")
    print("-" * 40)
    try:
        ep_vision = ep_robot.vision
        ep_camera = ep_robot.camera
        gestures = []

        def on_detect(gesture_info):
            with _vision_lock:
                gestures.clear()
                for x, y, w, h, info in gesture_info:
                    gestures.append((x, y, w, h, info))

        ep_camera.start_video_stream(display=False, resolution=camera.STREAM_720P)
        ep_vision.sub_detect_info(name="gesture", callback=on_detect)
        print("  Displaying 100 frames (press 'q' to skip)...")

        detected_count = 0
        for i in range(100):
            img = ep_camera.read_cv2_image(strategy="newest", timeout=0.5)
            with _vision_lock:
                for x, y, w, h, info in gestures:
                    pt1 = (int((x - w / 2) * 1280), int((y - h / 2) * 720))
                    pt2 = (int((x + w / 2) * 1280), int((y + h / 2) * 720))
                    cv2.rectangle(img, pt1, pt2, (0, 255, 0), 2)
                    cv2.putText(img, str(info), (pt1[0], pt1[1] - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                    detected_count += 1
            cv2.imshow("Gesture Detection", img)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()
        ep_vision.unsub_detect_info(name="gesture")
        ep_camera.stop_video_stream()
        print("[OK] Gesture detection done. Detections: {}".format(detected_count))
        return "PASS"
    except Exception as e:
        print("[FAIL] {}".format(e))
        return "FAIL"


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _print_summary(results):
    """Print a summary table of all test results."""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test_name, status in results.items():
        icon = "[PASS]" if status == "PASS" else "[WARN]" if status == "WARN" else "[FAIL]"
        print("  {:<20s} {}".format(test_name, icon))
    print("=" * 60)

    passed = sum(1 for s in results.values() if s == "PASS")
    total = len(results)
    print("Result: {}/{} tests passed.".format(passed, total))


if __name__ == "__main__":
    run_all_tests()
