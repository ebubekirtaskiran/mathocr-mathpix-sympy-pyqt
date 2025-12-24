# Bütün kütüphaneler:
import sys
import cv2
import base64
import requests
import sympy as sp
import os
import numpy as np
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QStatusBar, QMessageBox, QMainWindow, QFileDialog, QFrame, QDialog, QScrollArea
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
from datetime import datetime
import re

# Buton tasarımı
class ModernButton(QPushButton):
    def __init__(self, text, parent=None, color="#2d3436", hover_color="#353b48", pressed_color="#2f3640"):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}; color: #dfe6e9; border: 1px solid #636e72;
                padding: 10px 20px; border-radius: 5px; font-size: 14px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {hover_color}; border: 1px solid #718093; }}
            QPushButton:pressed {{ background-color: {pressed_color}; }}
        """)
        self.setMinimumHeight(40)

# Geçmiş penceresi
class HistoryDialog(QDialog):
    def __init__(self, history_items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("İşlem Geçmişi")
        self.setGeometry(200, 200, 800, 600)
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        for item in reversed(history_items):
            item_frame = QFrame()
            item_layout = QVBoxLayout(item_frame)
            time_label = QLabel(item['timestamp'])
            item_layout.addWidget(time_label)
            eq_label = QLabel("Orijinal Denklem:")
            item_layout.addWidget(eq_label)
            eq_image = QLabel()
            eq_image.setPixmap(item['equation_pixmap'].scaled(700, 80, Qt.KeepAspectRatio))
            item_layout.addWidget(eq_image)
            result_label = QLabel("Sonuç:")
            item_layout.addWidget(result_label)
            result_image = QLabel()
            result_image.setPixmap(item['result_pixmap'].scaled(700, 80, Qt.KeepAspectRatio))
            item_layout.addWidget(result_image)
            scroll_layout.addWidget(item_frame)
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

# Ana uygulama
class MathOCRApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Matematiksel İfade Tanıma")
        self.setGeometry(100, 100, 1000, 700)
        self.history = []
        self.initUI()

    def initUI(self):
        self.setStyleSheet("QMainWindow {background-color: #1e272e;} QLabel {color: #dfe6e9; font-size: 14px;}")
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        header = QLabel("Matematiksel İfade Tanıma")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #dfe6e9; padding: 5px;")
        layout.addWidget(header)

        self.video_label = QLabel(self)
        self.video_label.setMinimumSize(800, 450)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #2d3436; border-radius: 10px; border: 2px solid #636e72; padding: 10px;")
        layout.addWidget(self.video_label)

        button_layout = QHBoxLayout()
        self.add_buttons(button_layout)
        layout.addLayout(button_layout)

        result_frame = QFrame()
        result_layout = QVBoxLayout(result_frame)
        self.latex_label = QLabel()
        self.latex_label.setAlignment(Qt.AlignCenter)
        result_layout.addWidget(self.latex_label)
        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignCenter)
        result_layout.addWidget(self.result_label)
        layout.addWidget(result_frame)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Hazır")

        self.kamera = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def add_buttons(self, layout):
        self.load_image_button = ModernButton("Resim Yükle", color="#2980b9")
        self.load_image_button.clicked.connect(self.load_sample_image)
        layout.addWidget(self.load_image_button)

        self.capture_button = ModernButton("Kameradan İşlem Yap (Space)", color="#27ae60")
        self.capture_button.clicked.connect(self.capture_and_process)
        self.capture_button.setShortcut(Qt.Key_Space)
        layout.addWidget(self.capture_button)

        self.history_button = ModernButton("Geçmiş", color="#8e44ad")
        self.history_button.clicked.connect(self.show_history)
        layout.addWidget(self.history_button)

        self.clear_button = ModernButton("Temizle", color="#d35400")
        self.clear_button.clicked.connect(self.clear_results)
        layout.addWidget(self.clear_button)

        self.quit_button = ModernButton("Çıkış", color="#c0392b")
        self.quit_button.clicked.connect(self.close)
        layout.addWidget(self.quit_button)

    # LaTeX'ten Python uyumlu temizleme
    def clean_latex(self, expr_str):
        expr_str = expr_str.replace("\\left(", "(").replace("\\right)", ")").replace("\\log", "ln")
        expr_str = expr_str.replace("\\sin", "sin").replace("\\cos", "cos").replace("\\tan", "tan")
        expr_str = expr_str.replace("\\cot", "cot").replace("\\sec", "sec").replace("\\csc", "csc")
        expr_str = expr_str.replace("\\sqrt", "sqrt").replace("\\,", "")
        expr_str = re.sub(r'x\^{(\d+)}', r'x**\1', expr_str)
        expr_str = expr_str.strip()
        return expr_str

    # Mathpix sonrası işlem motoru
    def process_with_mathpix(self, frame):
        try:
            app_id = "your_app_ıd"
            app_key = "your_app_key"
            _, buffer = cv2.imencode('.png', frame)
            img_base64 = base64.b64encode(buffer).decode()
            headers = {'app_id': app_id, 'app_key': app_key, 'Content-type': 'application/json'}
            data = {'src': f'data:image/png;base64,{img_base64}', 'formats': ['latex_styled'], 'data_options': {'include_latex': True}}
            response = requests.post('https://api.mathpix.com/v3/text', json=data, headers=headers)
            result = response.json()

            if 'latex_styled' not in result:
                self.statusBar.showMessage("Mathpix çözümleme başarısız.")
                return

            latex_expr = result['latex_styled'].replace(r'\begin{array}{}', '').replace(r'\end{array}', '').replace(r'\\', '').strip()
            expr_str = self.clean_latex(latex_expr)
            print("OCR ->", expr_str)

            x = sp.Symbol('x')

            if r'\frac{d}{dx}' in latex_expr or r'd/dx' in latex_expr:
                body = expr_str.split('d}{dx}')[-1] if r'\frac{d}{dx}' in latex_expr else expr_str.split('d/dx')[-1]
                expr = sp.sympify(body, locals={'x': x})
                result_expr = sp.diff(expr, x)
            elif r'\lim' in latex_expr:
                match = re.search(r'\\lim_{x\\rightarrow([^}]+)}(.*)', latex_expr)
                limit_point, body = match.groups()
                expr = sp.sympify(self.clean_latex(body), locals={'x': x})
                result_expr = sp.limit(expr, x, sp.sympify(limit_point))
            elif r'\int' in latex_expr:
                match = re.search(r'\\int\s*(.*)dx', latex_expr)
                expr = sp.sympify(self.clean_latex(match.group(1)), locals={'x': x})
                result_expr = sp.integrate(expr, x)
            else:
                expr = sp.sympify(expr_str, locals={'x': x})
                result_expr = expr

            result_latex = sp.latex(result_expr).replace('**', '^').replace('*', '').replace('ln', '\\log')
            self.display_results(latex_expr, result_latex)
            self.statusBar.showMessage("Çözüm başarıyla gösterildi.")
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Hata: {str(e)}")

    # Ekrana sonuçları yaz
    def display_results(self, latex_expr, result_latex):
        eq_img = self.render_latex(latex_expr)
        res_img = self.render_latex(result_latex)
        self.latex_label.setPixmap(eq_img.scaled(self.latex_label.width(), 80, Qt.KeepAspectRatio))
        self.result_label.setPixmap(res_img.scaled(self.result_label.width(), 80, Qt.KeepAspectRatio))
        self.history.append({'timestamp': datetime.now().strftime("%d.%m.%Y %H:%M:%S"), 'equation_pixmap': eq_img, 'result_pixmap': res_img})

    def render_latex(self, latex_str):
        fig = plt.figure(figsize=(8, 2))
        plt.text(0.5, 0.5, f"${latex_str}$", ha='center', va='center', fontsize=20, color='#dfe6e9')
        plt.axis('off')
        canvas = FigureCanvas(fig)
        canvas.draw()
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, facecolor='#2d3436')
        buf.seek(0)
        img = QImage.fromData(buf.getvalue())
        plt.close(fig)
        return QPixmap.fromImage(img)

    # Kameradan oku
    def capture_and_process(self):
        ret, frame = self.kamera.read()
        if ret:
            self.process_with_mathpix(frame)

    # Dosyadan oku
    def load_sample_image(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Görüntü Seç', "", "Görüntü Dosyaları (*.png *.jpg *.jpeg)")
        if fname:
            frame = cv2.imdecode(np.fromfile(fname, dtype=np.uint8), cv2.IMREAD_COLOR)
            self.video_label.setPixmap(QPixmap(fname).scaled(self.video_label.size(), Qt.KeepAspectRatio))
            self.process_with_mathpix(frame)

    def clear_results(self):
        self.latex_label.clear()
        self.result_label.clear()
        self.statusBar.showMessage("Sonuçlar temizlendi")

    def update_frame(self):
        ret, frame = self.kamera.read()
        if ret:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = QImage(rgb, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(img).scaled(self.video_label.size(), Qt.KeepAspectRatio))

    def show_history(self):
        if not self.history:
            QMessageBox.information(self, "Geçmiş", "Henüz işlem geçmişi bulunmuyor.")
            return
        dialog = HistoryDialog(self.history, self)
        dialog.exec_()

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Çıkış', 'Çıkmak istiyor musunuz?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.kamera.release()
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MathOCRApp()
    window.show()
    sys.exit(app.exec_())
