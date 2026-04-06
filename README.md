# Robomaster EP Core — AI-Based Visual Interaction

AI-based real-time person tracking and hand gesture control for the DJI Robomaster EP Core. Developed as part of a Bachelor's thesis at the University of Oldenburg, Department of Computer Science (Systems Analysis and Optimization).

## Overview

This system enables natural human-robot interaction through two modes:

- **Tracking Mode** — The robot autonomously follows the closest person using YOLOv8 object detection and DeepSORT tracking, maintaining approximately 1 meter distance.
- **Gesture Mode** — The robot is controlled through hand gestures recognized via MediaPipe Hands. Gestures control chassis movement, robotic arm, and gripper.

Mode switching is done by showing **both fists** to the camera.

## Gesture Reference

| Fingers | Gesture | Robot Command | LED Color |
|---------|---------|---------------|-----------|
| 5 (open hand) | STOP | Stop all movement | Red |
| 3 (index + middle + ring) | FORWARD | Drive forward | Green |
| 1 (index only) | ARM_UP | Arm moves up | Blue |
| 2 (index + middle) | ARM_DOWN | Arm moves down | Cyan |
| 4 (all except thumb) | GRIPPER_OPEN | Gripper opens | Yellow |
| 0 (fist) | GRIPPER_CLOSE | Gripper closes | Magenta |

## Project Structure

```
├── main.py                              # Main entry point
├── requirements.txt                     # Python dependencies
├── config/
│   └── robot_config.py                  # Connection settings (STA mode, IP, resolution)
├── src/
│   ├── gesture/
│   │   ├── hand_landmark_viewer.py      # Live hand landmark visualization
│   │   ├── gesture_classifier.py        # Gesture recognition from landmarks
│   │   └── gesture_controller.py        # Gesture-to-robot-command mapping
│   ├── tracking/
│   │   ├── person_detector.py           # YOLOv8 person detection
│   │   ├── person_tracker.py            # DeepSORT tracking with follow-person selection
│   │   └── follow_controller.py         # Follow logic (distance + steering)
│   └── control/
│       └── decision_logic.py            # Mode switching (tracking / gesture)
├── tests/
│   ├── test_robot_connection.py         # Individual subsystem tests
│   └── test_robot_all.py               # Full system test (all subsystems)
└── docs/
    └── setup_guide_robomaster_connection.md  # Connection setup guide (German)
```

## Requirements

- Python 3.8
- DJI Robomaster EP Core
- Wi-Fi connection (STA mode) between robot and computer

## Installation

```bash
pip install -r requirements.txt
```

Dependencies: `robomaster`, `opencv-python`, `numpy`, `mediapipe==0.10.9`, `ultralytics`, `deep-sort-realtime`

## Usage

### Run the full system

```bash
python main.py
```

Starts in **Tracking Mode**. Show both fists to switch to **Gesture Mode**.

### Run gesture control only

```bash
python -m src.gesture.gesture_controller
```

### Run hand landmark viewer

```bash
python -m src.gesture.hand_landmark_viewer
```

### Run robot tests

Test all subsystems (connection, battery, chassis, camera, arm, gripper, LEDs, vision):

```bash
python -m tests.test_robot_all
```

Test a single subsystem:

```bash
python -m tests.test_robot_connection --test connection
python -m tests.test_robot_connection --test chassis
python -m tests.test_robot_connection --test camera
```

## Connection Setup

See [docs/setup_guide_robomaster_connection.md](docs/setup_guide_robomaster_connection.md) for a step-by-step guide on connecting the Robomaster EP Core via STA mode (German).

## License

MIT License — see [LICENSE](LICENSE) for details.
