"""
Person Detector — Detects persons in camera frames using YOLOv8.

Uses the ultralytics YOLOv8 model to detect persons (COCO class 0) in each
frame. Returns bounding boxes with confidence scores.

Usage:
    from src.tracking.person_detector import PersonDetector

    detector = PersonDetector()
    detections = detector.detect(frame)
"""

from ultralytics import YOLO

# COCO class index for "person"
PERSON_CLASS_ID = 0


class PersonDetector:
    """Detects persons in video frames using YOLOv8."""

    def __init__(self, model_name="yolov8n.pt", confidence_threshold=0.5):
        """
        Initialize the detector with a YOLOv8 model.

        Args:
            model_name: YOLOv8 model variant. "yolov8n.pt" is the nano model,
                        fastest but least accurate. Options: yolov8n, yolov8s,
                        yolov8m, yolov8l, yolov8x (increasing size/accuracy).
            confidence_threshold: Minimum confidence to accept a detection.
        """
        self._model = YOLO(model_name)
        self._confidence_threshold = confidence_threshold

    def detect(self, frame):
        """
        Detect all persons in a single frame.

        Args:
            frame: BGR image as numpy array (from OpenCV / robot camera).

        Returns:
            List of detections, each as a tuple:
            (x1, y1, x2, y2, confidence)
            where (x1, y1) is the top-left and (x2, y2) is the bottom-right
            corner of the bounding box in pixel coordinates.
        """
        results = self._model(frame, verbose=False)
        detections = []

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                # Only keep person detections above the confidence threshold
                if class_id == PERSON_CLASS_ID and confidence >= self._confidence_threshold:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    detections.append((
                        int(x1), int(y1), int(x2), int(y2), confidence
                    ))

        return detections
