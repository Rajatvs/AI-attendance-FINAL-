from pathlib import Path
import cv2


class Recognizer:
    def __init__(self, models_dir):
        self.models_dir = Path(models_dir)
        self.cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.recognizer = None
        self.labels = {}
        self.reload()

    def reload(self):
        self.recognizer = None
        model_path = self.models_dir / "trainer.yml"
        if hasattr(cv2, "face") and model_path.exists() and model_path.stat().st_size > 0:
            try:
                self.recognizer = cv2.face.LBPHFaceRecognizer_create()
                self.recognizer.read(str(model_path))
            except cv2.error:
                self.recognizer = None
        self._load_labels()

    def _load_labels(self):
        self.labels = {}
        labels_file = self.models_dir / "labels.txt"
        if labels_file.exists():
            for line in labels_file.read_text(encoding="utf-8").splitlines():
                if "," in line:
                    idx, name = line.split(",", 1)
                    try:
                        self.labels[int(idx)] = name.strip()
                    except ValueError:
                        pass

    def detect_and_recognize(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
        out = []
        for (x, y, w, h) in faces:
            name = "Unknown"
            confidence = 0.0
            if self.recognizer is not None:
                label, distance = self.recognizer.predict(gray[y:y+h, x:x+w])
                confidence = max(0.0, min(100.0, 100.0 - distance))
                # LBPH confidence here is a converted distance score; keep a conservative threshold.
                if confidence >= 45:
                    name = self.labels.get(label, "Unknown")
            out.append({"name": name, "confidence": round(confidence, 1), "box": [int(x), int(y), int(w), int(h)]})
        return out
