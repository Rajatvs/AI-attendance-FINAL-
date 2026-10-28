from pathlib import Path
import cv2
import json
import shutil


class FaceTrainer:
    """Collect face crops from camera frames and train an OpenCV LBPH recognizer."""

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.data_dir = self.base_dir / "data"
        self.faces_dir = self.data_dir / "face_samples"
        self.models_dir = self.base_dir / "models"
        self.faces_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.samples = {}

    def start(self, label_id: int, name: str):
        folder = self.faces_dir / str(label_id)
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)
        self.samples = {"label_id": label_id, "name": name, "count": 0, "folder": folder}
        return {"label_id": label_id, "name": name, "count": 0}

    def capture(self, frame):
        if not self.samples:
            raise RuntimeError("Training session has not been started.")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(90, 90))
        if len(faces) == 0:
            return {"captured": False, "count": self.samples["count"], "message": "No face detected"}

        # Use the largest detected face, which is normally the person standing in front of the camera.
        x, y, w, h = max(faces, key=lambda box: box[2] * box[3])
        face = gray[y:y + h, x:x + w]
        face = cv2.resize(face, (200, 200))
        self.samples["count"] += 1
        filename = self.samples["folder"] / f"face_{self.samples['count']:04d}.jpg"
        cv2.imwrite(str(filename), face)
        return {
            "captured": True,
            "count": self.samples["count"],
            "box": [int(x), int(y), int(w), int(h)],
            "message": "Face captured"
        }

    def train(self):
        if not self.samples:
            raise RuntimeError("Training session has not been started.")
        if self.samples["count"] < 20:
            raise RuntimeError("Capture at least 20 good face samples before training.")
        if not hasattr(cv2, "face"):
            raise RuntimeError("OpenCV face module is unavailable. Install opencv-contrib-python.")

        faces, labels = [], []
        folder = self.samples["folder"]
        for path in sorted(folder.glob("*.jpg")):
            img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                faces.append(img)
                labels.append(self.samples["label_id"])

        recognizer = cv2.face.LBPHFaceRecognizer_create(
            radius=1, neighbors=8, grid_x=8, grid_y=8
        )
        recognizer.train(faces, __import__("numpy").array(labels, dtype="int32"))
        trainer_path = self.models_dir / "trainer.yml"
        recognizer.write(str(trainer_path))

        # Keep the numeric ID -> student name mapping used by the recognition service.
        labels_file = self.models_dir / "labels.txt"
        existing = {}
        if labels_file.exists():
            for line in labels_file.read_text(encoding="utf-8").splitlines():
                if "," in line:
                    idx, label = line.split(",", 1)
                    try:
                        existing[int(idx)] = label.strip()
                    except ValueError:
                        pass
        existing[self.samples["label_id"]] = self.samples["name"]
        labels_file.write_text(
            "\n".join(f"{idx},{name}" for idx, name in sorted(existing.items())) + "\n",
            encoding="utf-8",
        )

        result = {
            "ok": True,
            "samples": len(faces),
            "trainer": str(trainer_path),
            "label_id": self.samples["label_id"],
            "name": self.samples["name"],
        }
        self.samples = {}
        return result
