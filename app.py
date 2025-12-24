import os
import sys
import cv2
import base64
import requests
import sympy as sp
from sympy.parsing.latex import parse_latex
from PyQt5.QtWidgets import (QApplication, QLabel, QPushButton, QVBoxLayout,
                             QWidget, QTextEdit, QHBoxLayout, QStatusBar,
                             QMessageBox, QMainWindow, QFileDialog)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QTimer, Qt


class MathOCRApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MathOCR with Mathpix + SymPy")
        self.setGeometry(100, 100, 1000, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Görüntü alanı
        self.video_label = QLabel(self)
        self.video_label.setMinimumSize(800, 600)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #22252B; border-radius: 10px;")
        main_layout.addWidget(self.video_label)

        # Butonlar
        button_layout = QHBoxLayout()

        self.load_image_button = QPushButton("Resim Yükle (Mathpix)")
        self.load_image_button.clicked.connect(self.load_sample_image)
        button_layout.addWidget(self.load_image_button)

        self.capture_button = QPushButton("Kameradan İşlem Yap (Mathpix)")
        self.capture_button.clicked.connect(self.capture_and_process)
        button_layout.addWidget(self.capture_button)

        self.clear_button = QPushButton("Temizle")
        self.clear_button.clicked.connect(self.clear_results)
        button_layout.addWidget(self.clear_button)

        self.quit_button = QPushButton("Çıkış")
        self.quit_button.clicked.connect(self.close)
        button_layout.addWidget(self.quit_button)

        main_layout.addLayout(button_layout)

        # Sonuç metin alanı
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("font-size: 16px; background-color: white; padding: 10px; border-radius: 10px;")
        self.result_text.setMinimumHeight(150)
        main_layout.addWidget(self.result_text)

        # Durum çubuğu
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Hazır")

        # Kamera başlat
        self.kamera = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def update_frame(self):
        ret, frame = self.kamera.read()
        if ret:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(rgb_frame, rgb_frame.shape[1], rgb_frame.shape[0], rgb_frame.strides[0], QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(image).scaled(
                self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def process_with_mathpix(self, frame):
        try:
            app_id = os.getenv("MATHPIX_APP_ID")
            app_key = os.getenv("MATHPIX_APP_KEY")

            if not app_id or not app_key:
                    QMessageBox.warning(self, "Eksik API Bilgisi", "MATHPIX_APP_ID / MATHPIX_APP_KEY .env içinde tanımlı değil.")
                    return

            _, buffer = cv2.imencode('.png', frame)
            img_base64 = base64.b64encode(buffer).decode()

            headers = {
                'app_id': app_id,
                'app_key': app_key,
                'Content-type': 'application/json'
            }

            data = {
                'src': f'data:image/png;base64,{img_base64}',
                'formats': ['latex_styled'],
                'data_options': {
                    'include_latex': True
                }
            }

            response = requests.post('https://api.mathpix.com/v3/text', json=data, headers=headers)
            result = response.json()

            if 'latex_styled' in result:
                latex_expr = result['latex_styled']

             # 🧹 Temizleme işlemleri
                latex_expr = latex_expr.replace(r'\begin{array}{}', '')
                latex_expr = latex_expr.replace(r'\end{array}', '')
                latex_expr = latex_expr.replace(r'\\', '')
                latex_expr = latex_expr.replace(r'\text{ integral }', '')
                latex_expr = latex_expr.replace(r'd x', 'dx')
                latex_expr = latex_expr.replace(r'\,', '')
                latex_expr = latex_expr.strip()

                self.statusBar.showMessage("LaTeX çözümleniyor...")
                print("Temizlenen LaTeX:", latex_expr)

                try:
                    sym_expr = parse_latex(latex_expr)
                    print("SymPy nesnesi:", sym_expr)

                    if hasattr(sym_expr, "doit"):
                        evaluated = sym_expr.doit()
                    else:
                        evaluated = sym_expr.evalf()

                    print("Değerlendirme sonucu:", evaluated)

                    # Sonucu arayüze yaz
                    self.result_text.clear()
                    self.result_text.append(f"LaTeX ifadesi:\n{latex_expr}\n")
                    self.result_text.append(f"Hesaplanan çözüm:\n{evaluated}")
                    self.statusBar.showMessage("Çözüm başarıyla gösterildi.")
                except Exception as e:
                    self.result_text.setText(f"LaTeX: {latex_expr}\n\nSymPy hata: {str(e)}")
            else:
                self.result_text.setText("Mathpix çözümleme başarısız.")
                self.statusBar.showMessage("Yanıt alınamadı.")
        except Exception as e:
            QMessageBox.warning(self, "Mathpix Hatası", f"Hata: {str(e)}")

    def capture_and_process(self):
        try:
            ret, frame = self.kamera.read()
            if ret:
                self.process_with_mathpix(frame)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Kameradan işlem alınamadı: {str(e)}")

    def load_sample_image(self):
        try:
            fname, _ = QFileDialog.getOpenFileName(self, 'Görüntü Seç', "", "Görüntü Dosyaları (*.png *.jpg *.jpeg)")
            if fname:
                frame = cv2.imread(fname)
                self.video_label.setPixmap(QPixmap(fname).scaled(
                    self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.process_with_mathpix(frame)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Resim yüklenemedi: {str(e)}")

    def clear_results(self):
        self.result_text.clear()
        self.statusBar.showMessage("Sonuçlar temizlendi")

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Çıkış',
                                   'Uygulamadan çıkmak istiyor musunuz?',
                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
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
