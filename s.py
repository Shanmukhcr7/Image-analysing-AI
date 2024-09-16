import os
import absl.logging
import sys
from PyQt5 import QtWidgets, QtCore, QtGui
from PIL import ImageGrab
import tkinter as tk
import PIL.Image
import google.generativeai as genai

# Set gRPC logging level to suppress initial warnings
os.environ['GRPC_VERBOSITY'] = 'ERROR'

genai.configure(api_key="YOUR GEMINI API KEY")

class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        # Set up logging without calling an incorrect method
        absl.logging.set_verbosity(absl.logging.INFO)
        absl.logging.use_absl_handler()

        root = tk.Tk()
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        self.setGeometry(0, 0, screen_width, screen_height)
        self.setWindowTitle(' ')
        self.begin = QtCore.QPoint()
        self.end = QtCore.QPoint()
        self.setWindowOpacity(0.3)
        QtWidgets.QApplication.setOverrideCursor(
            QtGui.QCursor(QtCore.Qt.CrossCursor)
        )
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        self.show()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setPen(QtGui.QPen(QtGui.QColor('black'), 3))
        qp.setBrush(QtGui.QColor(128, 128, 255, 128))
        qp.drawRect(QtCore.QRect(self.begin, self.end))

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = self.begin
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.close()

        x1 = min(self.begin.x(), self.end.x())
        y1 = min(self.begin.y(), self.end.y())
        x2 = max(self.begin.x(), self.end.x())
        y2 = max(self.begin.y(), self.end.y())

        img = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        img.save('screenshot.png')

        img = PIL.Image.open('screenshot.png')
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(["YOUR PROMPT", img], stream=True)
        response.resolve()
        
        response_text = response.text
        print_colored_response(response_text)

def print_colored_response(text):
    yellow = '\033[93m'
    green = '\033[92m'
    endc = '\033[0m'

    lines = text.split('\n')
    is_question = True  # Flag to track if the line is a question
    for line in lines:
        if is_question:
            print(f'{yellow}{line}{endc}')
            is_question = False
        elif '**' in line:  
            line = line.replace('**', f'{green}') + endc
            print(line)
        else:
            print(line)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MyWidget()
    window.show()
    app.aboutToQuit.connect(app.deleteLater)
    sys.exit(app.exec_())
