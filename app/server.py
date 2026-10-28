from flask import Flask, render_template, request, jsonify, send_file
from pathlib import Path
import base64, cv2, numpy as np
from .services.store import Store
from .services.recognizer import Recognizer
from .services.liveness import LivenessEngine
from .services.trainer import FaceTrainer

BASE = Path(__file__).resolve().parent.parent

def create_app():
    app = Flask(__name__, template_folder=str(BASE / "app" / "templates"), static_folder=str(BASE / "app" / "static"))
    store = Store(BASE / "data")
    recognizer = Recognizer(BASE / "models")
    liveness = LivenessEngine(BASE / "models")
    trainer = FaceTrainer(BASE)

    @app.get("/")
    def dashboard():
        stats = store.dashboard_stats()
        return render_template("dashboard.html", stats=stats)

    @app.get("/live")
    def live():
        return render_template("live.html")

    @app.get("/students")
    def students():
        return render_template("students.html", students=store.students())

    @app.get("/reports")
    def reports():
        return render_template("reports.html", rows=store.recent_attendance())


    @app.get("/train")
    def train_page():
        return render_template("train.html", students=store.students())

    @app.post("/api/training/start")
    def training_start():
        payload = request.get_json(force=True)
        student = store.get_student(payload.get("name", ""))
        if not student:
            return jsonify({"ok": False, "message": "Student not found. Add the student first."}), 404
        label_id = store.student_label_id(student["name"])
        return jsonify({"ok": True, **trainer.start(label_id, student["name"])})

    @app.post("/api/training/frame")
    def training_frame():
        payload = request.get_json(force=True)
        data = payload.get("image", "")
        if "," in data:
            data = data.split(",", 1)[1]
        try:
            raw = base64.b64decode(data)
            frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                return jsonify({"ok": False, "message": "Invalid camera frame"}), 400
            return jsonify({"ok": True, **trainer.capture(frame)})
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}), 500

    @app.post("/api/training/finish")
    def training_finish():
        try:
            result = trainer.train()
            recognizer.reload()
            return jsonify(result)
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}), 400

    @app.get("/api/stats")
    def stats():
        return jsonify(store.dashboard_stats())

    @app.get("/api/challenge")
    def challenge():
        return jsonify(liveness.new_challenge())

    @app.post("/api/scan")
    def scan():
        payload = request.get_json(force=True)
        data = payload.get("image", "")
        if "," in data:
            data = data.split(",", 1)[1]
        try:
            raw = base64.b64decode(data)
            frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
            if frame is None:
                return jsonify({"ok": False, "message": "Invalid camera frame"}), 400
            detections = recognizer.detect_and_recognize(frame)
            challenge = payload.get("challenge", {})
            primary_box = None
            recognized_name = None
            recognized_confidence = 0.0
            if detections:
                primary = max(detections, key=lambda d: d["box"][2] * d["box"][3])
                primary_box = primary["box"]
                if primary["name"] != "Unknown":
                    recognized_name = primary["name"]
                    recognized_confidence = primary["confidence"]

            live_result = liveness.evaluate(frame, challenge, primary_box)
            attendance = None
            if live_result["verified"] and recognized_name:
                attendance = store.mark_present(
                    recognized_name, recognized_confidence, "blink_verified"
                )
            return jsonify({
                "ok": True,
                "detections": detections,
                "liveness": live_result,
                "attendance": attendance,
            })
        except Exception as exc:
            return jsonify({"ok": False, "message": str(exc)}), 500

    @app.post("/api/attendance")
    def attendance():
        payload = request.get_json(force=True)
        name = payload.get("name")
        if not name:
            return jsonify({"ok": False, "message": "Student name is required"}), 400
        saved = store.mark_present(name, payload.get("confidence", 0), payload.get("liveness", "verified"))
        return jsonify({"ok": True, **saved})

    @app.post("/api/students")
    def add_student():
        payload = request.get_json(force=True)
        if not payload.get("name"):
            return jsonify({"ok": False, "message": "Name is required"}), 400
        return jsonify(store.add_student(payload["name"], payload.get("email", ""), payload.get("roll", "")))

    @app.get("/api/export")
    def export():
        path = store.export_csv()
        return send_file(path, as_attachment=True)

    return app
