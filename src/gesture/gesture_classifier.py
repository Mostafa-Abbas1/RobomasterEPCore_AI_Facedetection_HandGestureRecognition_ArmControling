"""
Gesture Classifier — Recognizes hand gestures from MediaPipe hand landmarks.

Determines which fingers are extended based on the 21 landmark positions
and maps the finger states to predefined gestures. Thumb detection is
intentionally excluded to avoid unreliable recognition.

Supported gestures:
    - STOP:          Open hand (5 fingers extended)
    - FORWARD:       Three fingers (index + middle + ring, no thumb, no pinky)
    - ARM_UP:        Only index finger extended
    - ARM_DOWN:      Index + middle finger extended
    - GRIPPER_OPEN:  Four fingers (all except thumb)
    - GRIPPER_CLOSE: Fist (0 fingers extended)
    - NONE:          No recognized gesture

Usage:
    from src.gesture.gesture_classifier import GestureClassifier

    classifier = GestureClassifier()
    gesture = classifier.classify(hand_landmarks, handedness)
"""


# Gesture name constants
GESTURE_STOP = "STOP"
GESTURE_FORWARD = "FORWARD"
GESTURE_ARM_UP = "ARM_UP"
GESTURE_ARM_DOWN = "ARM_DOWN"
GESTURE_GRIPPER_OPEN = "GRIPPER_OPEN"
GESTURE_GRIPPER_CLOSE = "GRIPPER_CLOSE"
GESTURE_NONE = "NONE"

# MediaPipe hand landmark indices
WRIST = 0
THUMB_CMC = 1
THUMB_MCP = 2
THUMB_IP = 3
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_DIP = 7
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_DIP = 11
MIDDLE_TIP = 12
RING_MCP = 13
RING_PIP = 14
RING_DIP = 15
RING_TIP = 16
PINKY_MCP = 17
PINKY_PIP = 18
PINKY_DIP = 19
PINKY_TIP = 20


class GestureClassifier:
    """Classifies hand gestures based on MediaPipe hand landmark positions."""

    def classify(self, hand_landmarks, handedness_label="Right"):
        """
        Classify a gesture from hand landmarks.

        Args:
            hand_landmarks: MediaPipe hand landmarks object with 21 landmarks.
            handedness_label: "Left" or "Right" indicating which hand is detected.

        Returns:
            A string constant representing the detected gesture.
        """
        landmarks = hand_landmarks.landmark
        finger_states = self._get_finger_states(landmarks, handedness_label)
        return self._map_gesture(finger_states)

    def _get_finger_states(self, landmarks, handedness_label):
        """
        Determine which fingers are extended.

        For the thumb, extension is checked horizontally (x-axis) because
        the thumb moves sideways rather than vertically.
        For other fingers, extension is checked vertically (y-axis) by
        comparing the TIP position to the PIP position. A lower y value
        means the fingertip is higher in the image.

        Args:
            landmarks: List of 21 hand landmark positions.
            handedness_label: "Left" or "Right" hand.

        Returns:
            List of 5 booleans: [thumb, index, middle, ring, pinky].
        """
        fingers = []

        # Thumb: compare TIP.x to IP.x
        # For right hand: thumb is extended if TIP is further left (lower x)
        # For left hand: thumb is extended if TIP is further right (higher x)
        if handedness_label == "Right":
            fingers.append(landmarks[THUMB_TIP].x < landmarks[THUMB_IP].x)
        else:
            fingers.append(landmarks[THUMB_TIP].x > landmarks[THUMB_IP].x)

        # Index finger: TIP higher than PIP (lower y = higher in image)
        fingers.append(landmarks[INDEX_TIP].y < landmarks[INDEX_PIP].y)

        # Middle finger
        fingers.append(landmarks[MIDDLE_TIP].y < landmarks[MIDDLE_PIP].y)

        # Ring finger
        fingers.append(landmarks[RING_TIP].y < landmarks[RING_PIP].y)

        # Pinky finger
        fingers.append(landmarks[PINKY_TIP].y < landmarks[PINKY_PIP].y)

        return fingers

    def _map_gesture(self, finger_states):
        """
        Map finger states to a gesture name.

        The mapping only considers the four non-thumb fingers for most gestures
        to avoid unreliable thumb detection causing gesture flickering.

        Args:
            finger_states: List of 5 booleans [thumb, index, middle, ring, pinky].

        Returns:
            A gesture name string constant.
        """
        thumb, index, middle, ring, pinky = finger_states

        # Count only non-thumb fingers for cleaner classification
        non_thumb_count = sum([index, middle, ring, pinky])

        # STOP: all 5 fingers extended (open hand)
        if non_thumb_count == 4 and thumb:
            return GESTURE_STOP

        # GRIPPER_OPEN: 4 fingers extended without thumb
        if index and middle and ring and pinky and not thumb:
            return GESTURE_GRIPPER_OPEN

        # FORWARD: index + middle + ring extended, pinky closed (thumb ignored)
        if index and middle and ring and not pinky:
            return GESTURE_FORWARD

        # ARM_DOWN: index + middle extended, ring and pinky closed (thumb ignored)
        if index and middle and not ring and not pinky:
            return GESTURE_ARM_DOWN

        # ARM_UP: only index finger extended, others closed (thumb ignored)
        if index and not middle and not ring and not pinky:
            return GESTURE_ARM_UP

        # GRIPPER_CLOSE: fist (no non-thumb fingers extended)
        if non_thumb_count == 0:
            return GESTURE_GRIPPER_CLOSE

        return GESTURE_NONE
