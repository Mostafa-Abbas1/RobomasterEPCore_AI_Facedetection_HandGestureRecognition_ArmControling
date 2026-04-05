"""
Person Tracker — Tracks detected persons across frames using DeepSORT.

Assigns persistent IDs to detected persons so the same person keeps the same
ID across frames. Selects the closest person (largest bounding box) as the
follow target.

Usage:
    from src.tracking.person_tracker import PersonTracker

    tracker = PersonTracker()
    tracks = tracker.update(detections, frame)
    target = tracker.get_target()
"""

from deep_sort_realtime.deepsort_tracker import DeepSort


class PersonTracker:
    """Tracks persons across frames and selects a follow target."""

    def __init__(self, max_age=30):
        """
        Initialize the tracker.

        Args:
            max_age: Number of frames a track is kept alive without a matching
                     detection. Higher values allow the tracker to remember a
                     person through longer occlusions.
        """
        self._tracker = DeepSort(max_age=max_age)
        self._target_id = None
        self._tracks = []

    @property
    def target_id(self):
        """The currently followed person's track ID, or None."""
        return self._target_id

    def update(self, detections, frame):
        """
        Update all tracks with new detections from the current frame.

        Args:
            detections: List of (x1, y1, x2, y2, confidence) tuples
                        from PersonDetector.detect().
            frame: The current BGR frame (used by DeepSORT for re-identification).

        Returns:
            List of active tracks. Each track has attributes:
            - track_id: Unique integer ID
            - to_ltrb(): Returns (left, top, right, bottom) bounding box
            - is_confirmed(): Whether the track is confirmed
        """
        # Convert detections to the format expected by DeepSORT:
        # list of ([left, top, width, height], confidence, class_name)
        ds_detections = []
        for x1, y1, x2, y2, conf in detections:
            w = x2 - x1
            h = y2 - y1
            ds_detections.append(([x1, y1, w, h], conf, "person"))

        self._tracks = self._tracker.update_tracks(ds_detections, frame=frame)
        self._update_target()
        return self._tracks

    def _update_target(self):
        """
        Select the follow target based on bounding box area (closest person).

        If the current target is still visible, keep following it.
        If the current target is lost, select the closest new person.
        """
        confirmed_tracks = [t for t in self._tracks if t.is_confirmed()]

        if not confirmed_tracks:
            # No persons visible — keep target ID in memory for re-acquisition
            return

        # Check if the current target is still among confirmed tracks
        if self._target_id is not None:
            for track in confirmed_tracks:
                if track.track_id == self._target_id:
                    return  # Target still visible, keep following

        # Target lost or no target set — select the closest person (largest box)
        largest_area = 0
        new_target_id = None
        for track in confirmed_tracks:
            left, top, right, bottom = track.to_ltrb()
            area = (right - left) * (bottom - top)
            if area > largest_area:
                largest_area = area
                new_target_id = track.track_id

        self._target_id = new_target_id

    def get_target(self):
        """
        Get the current follow target track.

        Returns:
            The target track object, or None if no target is available.
        """
        if self._target_id is None:
            return None

        for track in self._tracks:
            if track.track_id == self._target_id and track.is_confirmed():
                return track

        return None

    def clear_target(self):
        """Reset the target ID. Used when switching to gesture mode."""
        self._target_id = None
