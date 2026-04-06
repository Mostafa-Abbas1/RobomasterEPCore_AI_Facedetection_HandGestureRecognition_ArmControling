"""
Follow Controller — Controls robot movement to follow a tracked person.

Uses the target person's bounding box position and size to determine:
- Horizontal steering: Turn left/right to keep the person centered.
- Distance control: Drive forward/backward to maintain ~1 meter distance.

The target distance is estimated from the bounding box height relative to the
frame height. A person at ~1 meter typically fills about 60-70% of a 720p frame.

Usage:
    from src.tracking.follow_controller import FollowController

    controller = FollowController()
    controller.follow(target_track, frame_shape, ep_chassis)
"""

# Target bounding box height ratio (box height / frame height).
# When the person's box fills this fraction of the frame, the robot is at
# approximately the desired distance (1 meter).
TARGET_BOX_RATIO = 0.55

# Tolerance band around the target ratio. The robot won't move forward/backward
# if the ratio is within TARGET_BOX_RATIO +/- DISTANCE_TOLERANCE.
DISTANCE_TOLERANCE = 0.08

# Horizontal center tolerance. If the person's center x is within this fraction
# of the frame center, no rotation is applied. (0.1 = 10% of frame width)
CENTER_TOLERANCE = 0.1

# Movement speeds (intentionally very slow to avoid losing the target)
FORWARD_SPEED = 0.08         # m/s — approach speed
BACKWARD_SPEED = 0.05        # m/s — retreat speed
MAX_ROTATION_SPEED = 10      # degrees/s — maximum turning speed

# If the robot lost the target in the previous frame, it should not move.
# Number of consecutive frames with a valid target before the robot starts moving.
FRAMES_BEFORE_MOVING = 3


class FollowController:
    """Controls the robot chassis to follow a tracked person."""

    def __init__(self):
        self._consecutive_target_frames = 0

    def follow(self, target_track, frame_shape, ep_chassis):
        """
        Calculate and send chassis commands to follow the target person.

        Args:
            target_track: A DeepSORT track object with to_ltrb() method.
            frame_shape: Tuple (height, width, channels) of the camera frame.
            ep_chassis: Robot chassis module for sending drive commands.

        Returns:
            A dict with debug info: {"x_speed", "z_speed", "box_ratio",
            "center_offset"} for display or logging.
        """
        self._consecutive_target_frames += 1
        frame_h, frame_w = frame_shape[:2]
        left, top, right, bottom = target_track.to_ltrb()

        # --- Distance control (forward / backward) ---
        box_height = bottom - top
        box_ratio = box_height / frame_h

        x_speed = 0.0
        if box_ratio < TARGET_BOX_RATIO - DISTANCE_TOLERANCE:
            x_speed = FORWARD_SPEED
        elif box_ratio > TARGET_BOX_RATIO + DISTANCE_TOLERANCE:
            x_speed = -BACKWARD_SPEED

        # --- Horizontal steering (rotation) ---
        person_center_x = (left + right) / 2.0
        frame_center_x = frame_w / 2.0
        # Normalized offset: -1.0 (far left) to +1.0 (far right)
        center_offset = (person_center_x - frame_center_x) / frame_center_x

        z_speed = 0.0
        if abs(center_offset) > CENTER_TOLERANCE:
            # Proportional steering: the further off-center, the faster the turn.
            # Clamped to MAX_ROTATION_SPEED.
            # Positive center_offset (person right) → robot turns right (z < 0)
            # Negative center_offset (person left) → robot turns left (z > 0)
            z_speed = center_offset * MAX_ROTATION_SPEED
            z_speed = max(-MAX_ROTATION_SPEED, min(MAX_ROTATION_SPEED, z_speed))

        # Only start moving after the target has been stable for a few frames.
        # This prevents the robot from jerking when a target briefly appears.
        if self._consecutive_target_frames < FRAMES_BEFORE_MOVING:
            x_speed = 0.0
            z_speed = 0.0

        ep_chassis.drive_speed(x=x_speed, y=0, z=z_speed)

        return {
            "x_speed": x_speed,
            "z_speed": z_speed,
            "box_ratio": box_ratio,
            "center_offset": center_offset,
        }

    def stop(self, ep_chassis):
        """Stop all chassis movement and reset the frame counter."""
        self._consecutive_target_frames = 0
        ep_chassis.drive_speed(x=0, y=0, z=0)
