# AttendAI — Automated AI Attendance System

A professional, local-first attendance application designed around:
- Live face detection
- LBPH face recognition
- Active liveness verification (randomized challenge)
- Blink/head-motion verification hooks
- Attendance de-duplication
- Excel export
- Student registration/training
- Dashboard and reports

## Important
This repository is intentionally delivered as source code plus a Windows build pipeline.
The chat environment cannot compile a native Windows `.exe`, so the included `BUILD_WINDOWS.bat`
creates the Windows executable on a Windows machine.

The application does NOT claim that blink detection alone can stop replay attacks. The live mode
uses a randomized active challenge concept so a prerecorded video cannot simply be replayed unless
it happens to satisfy the fresh challenge.

## Quick start on Windows

1. Install Python 3.11 (64-bit).
2. Run `BUILD_WINDOWS.bat`.
3. Run `run_attendance.bat`.
4. Open the local address shown in the terminal.

For a recruiter demo, keep this source folder available so you can explain and modify the code.

## Model files
Place your trained LBPH model at:
`models/trainer.yml`

For dlib landmark liveness, place:
`models/shape_predictor_68_face_landmarks.dat`

If a YOLOv6 model is available, place its weights/config under `models/yolov6/` and implement
the adapter in `app/services/detector.py`. The current detector falls back to OpenCV Haar so the
demo can still run without a YOLO checkpoint.

## Data
Student profiles live in `data/students.json`.
Attendance is written to `data/attendance.xlsx`.

## Anti-proxy design
A prerecorded face video is a replay attack. A static "blink twice" rule can be defeated if
the recorded video contains two blinks. This project therefore supports a randomized challenge:
the UI asks for actions such as `BLINK`, `TURN LEFT`, or `TURN RIGHT` in a random order. The
challenge is generated after the person is detected, so an old recording cannot know the new
sequence. For production security, add a dedicated presentation-attack detector / depth or IR
sensor and treat this software liveness as a practical prototype, not a certified biometric system.

## Face training
Open **Students → Register & train face**. Select the student, start the 15-second capture, and slowly turn the head through different angles. The server captures grayscale face crops and, after at least 20 good samples, trains an OpenCV LBPH recognizer. A real `models/trainer.yml` is generated from the captured person's face; it cannot be pre-generated meaningfully without their camera samples. The numeric label-to-name mapping is saved in `models/labels.txt`.
