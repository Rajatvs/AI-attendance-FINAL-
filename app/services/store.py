from pathlib import Path
from datetime import datetime
import json, csv

class Store:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.students_file = self.data_dir / "students.json"
        self.attendance_file = self.data_dir / "attendance.csv"
        if not self.students_file.exists():
            self.students_file.write_text(json.dumps([
                {"name": "Rajat VS", "email": "rajat@example.com", "roll": "AI001"},
                {"name": "Demo Student", "email": "demo@example.com", "roll": "AI002"}
            ], indent=2), encoding="utf-8")
        if not self.attendance_file.exists():
            self.attendance_file.write_text("date,time,name,confidence,liveness,status\n", encoding="utf-8")

    def students(self):
        return json.loads(self.students_file.read_text(encoding="utf-8"))

    def add_student(self, name, email="", roll=""):
        rows = self.students()
        item = {"name": name, "email": email, "roll": roll}
        rows.append(item)
        self.students_file.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return {"ok": True, "student": item}

    def get_student(self, name):
        name = name.strip().lower()
        for student in self.students():
            if student.get("name", "").strip().lower() == name:
                return student
        return None

    def student_label_id(self, name):
        rows = self.students()
        for index, student in enumerate(rows, start=1):
            if student.get("name", "").strip().lower() == name.strip().lower():
                return index
        raise ValueError("Student is not registered.")

    def recent_attendance(self, limit=50):
        with self.attendance_file.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return list(reversed(rows[-limit:]))

    def mark_present(self, name, confidence, liveness):
        today = datetime.now().strftime("%Y-%m-%d")
        rows = self.recent_attendance(10000)
        if any(r["date"] == today and r["name"] == name and r["status"] == "PRESENT" for r in rows):
            return {"duplicate": True, "message": "Attendance already recorded for today."}
        now = datetime.now()
        with self.attendance_file.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([today, now.strftime("%H:%M:%S"), name, round(float(confidence), 2), liveness, "PRESENT"])
        return {"duplicate": False, "message": f"Attendance marked for {name}."}

    def dashboard_stats(self):
        total = len(self.students())
        rows = self.recent_attendance(10000)
        today = datetime.now().strftime("%Y-%m-%d")
        present = {r["name"] for r in rows if r["date"] == today and r["status"] == "PRESENT"}
        p = len(present)
        return {"students": total, "present": p, "absent": max(0, total-p), "rate": round((p/total*100) if total else 0, 1)}

    def export_csv(self):
        return str(self.attendance_file)
