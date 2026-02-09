import sys
import warnings
import absl.logging
import threading
import base64
import requests
import io
import time
from queue import Queue

from PyQt5 import QtWidgets, QtCore, QtGui
from PIL import ImageGrab, Image
import google.generativeai as genai
import warnings
warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module="google.api_core"
)

# ─────────────────────────────
# CONFIG
# ─────────────────────────────
warnings.filterwarnings("ignore", category=FutureWarning)
absl.logging.set_verbosity(absl.logging.ERROR)

# Gemini
GEMINI_API_KEY = "AIzaSyAzFtQeq8iz2GRkghmYtXG2v-ZVnUs2rC8"
GEMINI_MODEL = "gemini-2.5-flash-preview-09-2025"
genai.configure(api_key=GEMINI_API_KEY)

# NVIDIA
NVIDIA_API_KEY = "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"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "nvidia/nemotron-nano-12b-v2-vl"

# Shared result queue
results_queue = Queue()
EXPECTED_RESULTS = 2


# ─────────────────────────────
# UTILS
# ─────────────────────────────
def pil_to_base64(img: Image.Image):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def push_result(source, text):
    results_queue.put((time.time(), source, text))


# ─────────────────────────────
# MODEL CALLS
# ─────────────────────────────
def run_gemini(image):
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        prompt = (
            "This image contains a multiple-choice question. "
            "Reply with ONLY the correct option text or letter."
        )
        response = model.generate_content([prompt, image])
        answer = (response.text or "").strip()
        if answer:
            push_result("Gemini", answer)
    except Exception as e:
        push_result("Gemini", f"ERROR: {e}")


def run_nvidia(image):
    try:
        img_b64 = pil_to_base64(image)

        payload = {
            "model": NVIDIA_MODEL,
            "messages": [
                {"role": "system", "content": "/think"},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "give me only correct option name and nothing else and no explanations"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}"
                            },
                        },
                    ],
                },
            ],
            "max_tokens": 512,
        }

        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        }

        r = requests.post(NVIDIA_URL, headers=headers, json=payload, timeout=20)
        data = r.json()

        answer = (
            data["choices"][0]["message"]["content"].strip()
            if "choices" in data
            else "No response"
        )

        push_result("NVIDIA", answer)

    except Exception as e:
        push_result("NVIDIA", f"ERROR: {e}")


# ─────────────────────────────
# UI
# ─────────────────────────────
class ScreenshotOverlay(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()
        self.done = False

        screen = QtWidgets.QApplication.primaryScreen()
        self.setGeometry(screen.geometry())

        self.setWindowOpacity(0.35)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )

        QtWidgets.QApplication.setOverrideCursor(
            QtGui.QCursor(QtCore.Qt.CrossCursor)
        )

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(QtGui.QColor(0, 120, 215), 2))
        painter.setBrush(QtGui.QColor(0, 120, 215, 60))
        painter.drawRect(QtCore.QRect(self.begin, self.end))

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = self.begin

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        if self.done:
            return
        self.done = True
        self.hide()
        QtWidgets.QApplication.restoreOverrideCursor()
        QtCore.QTimer.singleShot(0, self.process)

    def process(self):
        x1, y1 = min(self.begin.x(), self.end.x()), min(self.begin.y(), self.end.y())
        x2, y2 = max(self.begin.x(), self.end.x()), max(self.begin.y(), self.end.y())

        if x2 - x1 < 10 or y2 - y1 < 10:
            QtWidgets.QApplication.quit()
            return

        image = ImageGrab.grab(bbox=(x1, y1, x2, y2))

        print("\n--- Analyzing (Gemini + NVIDIA) ---\n")

        threading.Thread(target=run_gemini, args=(image,), daemon=True).start()
        threading.Thread(target=run_nvidia, args=(image,), daemon=True).start()

        QtCore.QTimer.singleShot(100, self.collect_results)

    def collect_results(self):
        results = []

        while len(results) < EXPECTED_RESULTS:
            ts, src, ans = results_queue.get()
            results.append((ts, src, ans))

        # Sort by arrival time
        results.sort(key=lambda x: x[0])

        BOLD = "\033[1m"
        CYAN = "\033[96m"
        END = "\033[0m"

        for i, (_, src, ans) in enumerate(results, 1):
            print(f"{BOLD}{i}. RESPONSE FROM {src}:{END}")
            print(f"{CYAN}{ans}{END}\n")

        QtWidgets.QApplication.quit()


# ─────────────────────────────
# MAIN
# ─────────────────────────────
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    overlay = ScreenshotOverlay()
    overlay.show()
    sys.exit(app.exec_())
