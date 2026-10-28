from pathlib import Path
import cv2
import numpy as np

try:
    import dlib
except ImportError:
    dlib = None


class LivenessEngine:
    """Simple temporal blink-based liveness check.

    If a dlib 68-point landmark model is present at
    models/shape_predictor_68_face_landmarks.dat, EAR is used.
    Otherwise an OpenCV eye-cascade fallback is used so the demo still works.

    A blink is counted on an open -> closed -> open transition. Two blinks
    are required before the session is verified.
    """

    LEFT_EYE = list(range(36, 42))
    RIGHT_EYE = list(range(42, 48))

    def __init__(self, models_dir):
        self.models_dir = Path(models_dir)
        self.predictor = None
        self.detector = dlib.get_frontal_face_detector() if dlib else None

        predictor_path = self.models_dir / "shape_predictor_68_face_landmarks.dat"
        if dlib and predictor_path.exists():
            try:
                self.predictor = dlib.shape_predictor(str(predictor_path))
            except Exception:
                self.predictor = None

        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_eye.xml"
        )
        self.reset()

    def reset(self):
        self.blink_count = 0
        self.eye_was_closed = False
        self.verified = False
        self.last_message = "Waiting for two blinks..."

    def new_challenge(self):
        self.reset()
        return {
            "sequence": ["BLINK", "BLINK"],
            "current": "BLINK",
            "progress": 0,
            "total": 2,
        }

    @staticmethod
    def _ear(points):
        # Eye Aspect Ratio using the standard 6 landmark points.
        p1, p2, p3, p4, p5, p6 = points
        vertical_1 = np.linalg.norm(p2 - p6)
        vertical_2 = np.linalg.norm(p3 - p5)
        horizontal = np.linalg.norm(p1 - p4)
        if horizontal == 0:
            return 1.0
        return (vertical_1 + vertical_2) / (2.0 * horizontal)

    def _dlib_eye_state(self, gray, box):
        if not self.predictor or not self.detector:
            return None

        x, y, w, h = box
        rect = dlib.rectangle(int(x), int(y), int(x + w), int(y + h))
        shape = self.predictor(gray, rect)
        pts = np.array([[shape.part(i).x, shape.part(i).y] for i in range(68)])
        left = self._ear(pts[self.LEFT_EYE])
        right = self._ear(pts[self.RIGHT_EYE])
        ear = (left + right) / 2.0
        # Typical EAR threshold; actual value varies by camera/person.
        return ear < 0.22

    def _cascade_eye_state(self, gray, box):
        x, y, w, h = box
        roi = gray[y:y + h, x:x + w]
        if roi.size == 0:
            return None
        roi = cv2.equalizeHist(roi)
        eyes = self.eye_cascade.detectMultiScale(
            roi,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(18, 18),
        )
        # Two visible eyes normally means open. Zero eyes means likely closed,
        # though occlusion/pose can also produce zero detections.
        return len(eyes) == 0

    def evaluate(self, frame, challenge=None, face_box=None):
        if self.verified:
            return {
                "verified": True,
                "current": None,
                "progress": 2,
                "total": 2,
                "blink_count": self.blink_count,
                "message": "Liveness verified. Attendance can be recorded.",
            }

        if face_box is None:
            return {
                "verified": False,
                "current": "BLINK",
                "progress": self.blink_count,
                "total": 2,
                "blink_count": self.blink_count,
                "message": "Face detected. Blink twice to verify liveness.",
            }

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        closed = self._dlib_eye_state(gray, face_box)
        if closed is None:
            closed = self._cascade_eye_state(gray, face_box)

        if closed is None:
            return {
                "verified": False,
                "current": "BLINK",
                "progress": self.blink_count,
                "total": 2,
                "blink_count": self.blink_count,
                "message": "Could not evaluate eyes. Face the camera clearly.",
            }

        # Count only the transition from closed back to open.
        if closed:
            self.eye_was_closed = True
            self.last_message = "Eyes closed — open them to complete the blink."
        elif self.eye_was_closed:
            self.blink_count += 1
            self.eye_was_closed = False
            if self.blink_count >= 2:
                self.verified = True
                self.last_message = "Two blinks verified. Attendance can be recorded."
            else:
                self.last_message = f"Blink {self.blink_count}/2 verified. Blink once more."
        else:
            self.last_message = f"Blink {self.blink_count}/2 — blink twice to verify."

        return {
            "verified": self.verified,
            "current": None if self.verified else "BLINK",
            "progress": min(self.blink_count, 2),
            "total": 2,
            "blink_count": self.blink_count,
            "message": self.last_message,
        }
