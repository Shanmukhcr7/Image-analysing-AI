import sys
import warnings
import absl.logging
import threading
import base64
import requests
import io
import time
import keyboard
import os
from queue import Queue, Empty

from PyQt5 import QtWidgets, QtCore, QtGui
from PIL import ImageGrab, Image
import google.generativeai as genai

# ─────────────────────────────
# CONFIG & COLORS
# ─────────────────────────────
warnings.filterwarnings("ignore", category=FutureWarning)
absl.logging.set_verbosity(absl.logging.ERROR)

# ANSI Color Codes for neat terminal output
CLR_MODEL = "\033[94m"    # Blue
CLR_ANS   = "\033[92m"    # Green
CLR_TIME  = "\033[93m"    # Yellow
CLR_ERR   = "\033[91m"    # Red
CLR_RESET = "\033[0m"     # Reset
CLR_BOLD  = "\033[1m"

# 🔑 API KEYS
GEMINI_API_KEY = "AIzaSyAhdoTIkEPOGEHHfGmcZxmdpDJSCXohghU"
NVIDIA_API_KEY_QWEN = "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"
NVIDIA_API_KEY_MISTRAL = "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"

# Models
GEMINI_MODEL_NAME = "gemini-2.5-flash"
QWEN_MODEL_NAME = "qwen/qwen3.5-397b-a17b"
MISTRAL_MODEL_NAME = "mistralai/mistral-large-3-675b-instruct-2512"

genai.configure(api_key=GEMINI_API_KEY)
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

results_queue = Queue()
MODEL_TIMEOUT = 15

selected_bbox = None
overlay_instance = None
highlight_instance = None

# ─────────────────────────────
# UTILS
# ─────────────────────────────
def clean_error(err_msg):
    """Detects quota errors and returns a neat 'NO QUOTA' string."""
    err_str = str(err_msg).lower()
    if "429" in err_str or "quota" in err_str or "limit" in err_str:
        return f"{CLR_ERR}NO QUOTA{CLR_RESET}"
    return f"{CLR_ERR}Error: {err_str[:25]}...{CLR_RESET}"

def prepare_image(img: Image.Image):
    max_dim = 1024
    if max(img.size) > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=80)
    return buf.getvalue()

def push_result(source, text, duration):
    results_queue.put((source, text, duration))

# ─────────────────────────────
# MODEL CALLS
# ─────────────────────────────
def run_gemini(img_bytes):
    start = time.perf_counter()
    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        img_part = {"mime_type": "image/jpeg", "data": img_bytes}
        prompt = "Multiple choice question. Reply ONLY with the correct option text/letter."
        response = model.generate_content([prompt, img_part])
        answer = (response.text or "").strip()
        push_result("Gemini 2.5", f"{CLR_ANS}{answer}{CLR_RESET}", time.perf_counter() - start)
    except Exception as e:
        push_result("Gemini 2.5", clean_error(e), time.perf_counter() - start)

def run_qwen(img_bytes):
    start = time.perf_counter()
    try:
        img_b64 = base64.b64encode(img_bytes).decode()
        payload = {
            "model": QWEN_MODEL_NAME,
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Solve. Give only the answer."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]}],
            "max_tokens": 64, "temperature": 0.1
        }
        headers = {"Authorization": f"Bearer {NVIDIA_API_KEY_QWEN}", "Accept": "application/json"}
        r = requests.post(NVIDIA_URL, headers=headers, json=payload, timeout=MODEL_TIMEOUT)
        data = r.json()
        if "error" in data: raise Exception(str(data["error"]))
        answer = data["choices"][0]["message"]["content"].strip()
        push_result("Qwen 3.5  ", f"{CLR_ANS}{answer}{CLR_RESET}", time.perf_counter() - start)
    except Exception as e:
        push_result("Qwen 3.5  ", clean_error(e), time.perf_counter() - start)

def run_mistral(img_bytes):
    start = time.perf_counter()
    try:
        # OCR Step
        ocr_model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        ocr_res = ocr_model.generate_content(["Extract question text.", {"mime_type": "image/jpeg", "data": img_bytes}])
        question_text = ocr_res.text
        
        payload = {
            "model": MISTRAL_MODEL_NAME,
            "messages": [{"role": "user", "content": f"Answer this: {question_text}. Give only option text/letter."}],
            "max_tokens": 64, "temperature": 0.1
        }
        headers = {"Authorization": f"Bearer {NVIDIA_API_KEY_MISTRAL}", "Accept": "application/json"}
        r = requests.post(NVIDIA_URL, headers=headers, json=payload, timeout=MODEL_TIMEOUT)
        data = r.json()
        if "error" in data: raise Exception(str(data["error"]))
        answer = data["choices"][0]["message"]["content"].strip()
        push_result("Mistral 3 ", f"{CLR_ANS}{answer}{CLR_RESET}", time.perf_counter() - start)
    except Exception as e:
        push_result("Mistral 3 ", clean_error(e), time.perf_counter() - start)

# ─────────────────────────────
# CONTROL LOGIC
# ─────────────────────────────
def capture_and_analyze():
    if not selected_bbox: return
    print(f"\n{CLR_BOLD}🔍 SCANNING AREA...{CLR_RESET}")
    
    image = ImageGrab.grab(bbox=selected_bbox, all_screens=True)
    img_bytes = prepare_image(image)

    threading.Thread(target=run_gemini, args=(img_bytes,), daemon=True).start()
    threading.Thread(target=run_qwen, args=(img_bytes,), daemon=True).start()
    threading.Thread(target=run_mistral, args=(img_bytes,), daemon=True).start()
    threading.Thread(target=collect_results, daemon=True).start()

def collect_results():
    received = 0
    start_time = time.perf_counter()
    while time.perf_counter() - start_time < 15:
        try:
            src, ans, duration = results_queue.get(timeout=0.1)
            # Neat output format
            print(f" {CLR_MODEL}{src}{CLR_RESET} | {ans:<20} | {CLR_TIME}{duration:.2f}s{CLR_RESET}")
            received += 1
            if received == 3: break
        except Empty:
            continue

def trigger_reselect():
    QtCore.QMetaObject.invokeMethod(overlay_instance, "show_overlay", QtCore.Qt.QueuedConnection)

def exit_app():
    print(f"\n{CLR_ERR}🛑 EXITING...{CLR_RESET}")
    os._exit(0)

# ─────────────────────────────
# UI COMPONENTS
# ─────────────────────────────
class HighlightFrame(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.WindowTransparentForInput | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.rect_to_draw = QtCore.QRect()

    def update_position(self, bbox):
        x1, y1, x2, y2 = bbox
        self.setGeometry(x1-2, y1-2, (x2-x1)+4, (y2-y1)+4)
        self.rect_to_draw = QtCore.QRect(1, 1, (x2-x1)+1, (y2-y1)+1)
        self.show()
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 0, 0, 200), 2, QtCore.Qt.DashLine))
        painter.drawRect(self.rect_to_draw)

class ScreenshotOverlay(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

    @QtCore.pyqtSlot()
    def show_overlay(self):
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))
        self.show()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 160))
        if not self.begin.isNull() and not self.end.isNull():
            rect = QtCore.QRect(self.begin, self.end).normalized()
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            painter.fillRect(rect, QtCore.Qt.transparent)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            painter.setPen(QtGui.QPen(QtGui.QColor(0, 255, 255), 2))
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.update()

    def mouseMoveEvent(self, event):
        if not self.begin.isNull():
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        global selected_bbox
        rect = QtCore.QRect(self.begin, self.end).normalized()
        if rect.width() > 10:
            p1 = self.mapToGlobal(rect.topLeft())
            p2 = self.mapToGlobal(rect.bottomRight())
            selected_bbox = (p1.x(), p1.y(), p2.x(), p2.y())
            highlight_instance.update_position(selected_bbox)
        QtWidgets.QApplication.restoreOverrideCursor()
        self.hide()
        self.begin = QtCore.QPoint() # Reset

# ─────────────────────────────
# MAIN
# ─────────────────────────────
if __name__ == "__main__":
    # Windows ANSI support
    os.system('') 
    app = QtWidgets.QApplication(sys.argv)
    
    overlay_instance = ScreenshotOverlay()
    highlight_instance = HighlightFrame()
    overlay_instance.show_overlay()

    keyboard.add_hotkey("q", capture_and_analyze)
    keyboard.add_hotkey("r", trigger_reselect)
    keyboard.add_hotkey("x", exit_app)
    
    print(f"{CLR_BOLD}--- AI MULTI-SOLVER READY ---{CLR_RESET}")
    print(f"{CLR_MODEL}[q]{CLR_RESET} Solve | {CLR_MODEL}[r]{CLR_RESET} Reselect | {CLR_MODEL}[x]{CLR_RESET} Exit")
    print("-" * 45)
    
    sys.exit(app.exec_())