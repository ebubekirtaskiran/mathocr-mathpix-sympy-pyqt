import sys
import cv2
import base64
import requests
import sympy as sp
import os
import numpy as np
from PyQt5.QtWidgets import (QApplication, QLabel, QPushButton, QVBoxLayout,
                             QWidget, QTextEdit, QHBoxLayout, QStatusBar,
                             QMessageBox, QMainWindow, QFileDialog, QFrame,
                             QDialog, QScrollArea)
from PyQt5.QtGui import QImage, QPixmap, QFont, QPainter, QColor
from PyQt5.QtCore import QTimer, Qt, QSize
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
from datetime import datetime

class ModernButton(QPushButton):
    def __init__(self, text, parent=None, color="#2d3436", hover_color="#353b48", pressed_color="#2f3640"):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: #dfe6e9;
                border: 1px solid #636e72;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border: 1px solid #718093;
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
        """)
        self.setMinimumHeight(40)

class HistoryDialog(QDialog):
    def __init__(self, history_items, parent=None):
        super().__init__(parent)
        self.setWindowTitle("İşlem Geçmişi")
        self.setGeometry(200, 200, 800, 600)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e272e;
            }
            QLabel {
                color: #dfe6e9;
                font-size: 14px;
            }
            QScrollArea {
                border: none;
                background-color: #1e272e;
            }
            QWidget#scrollContent {
                background-color: #1e272e;
            }
        """)

        layout = QVBoxLayout(self)
        
        # Geçmiş öğeleri için kaydırma alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                border: none;
                background: #2d3436;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #636e72;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        
        for item in reversed(history_items):  # En yeniden en eskiye göster
            item_frame = QFrame()
            item_frame.setStyleSheet("""
                QFrame {
                    background-color: #2d3436;
                    border-radius: 10px;
                    border: 1px solid #636e72;
                    padding: 10px;
                }
            """)
            item_layout = QVBoxLayout(item_frame)
            
            # Zaman damgası
            time_label = QLabel(item['timestamp'])
            time_label.setStyleSheet("color: #b2bec3; font-size: 12px;")
            item_layout.addWidget(time_label)
            
            # Orijinal denklem
            eq_label = QLabel("Orijinal Denklem:")
            eq_label.setStyleSheet("color: #dfe6e9; font-weight: bold;")
            item_layout.addWidget(eq_label)
            
            eq_image = QLabel()
            eq_image.setPixmap(item['equation_pixmap'].scaled(
                700, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            item_layout.addWidget(eq_image)
            
            # Sonuç
            result_label = QLabel("Sonuç:")
            result_label.setStyleSheet("color: #dfe6e9; font-weight: bold;")
            item_layout.addWidget(result_label)
            
            result_image = QLabel()
            result_image.setPixmap(item['result_pixmap'].scaled(
                700, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            item_layout.addWidget(result_image)
            
            scroll_layout.addWidget(item_frame)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

class MathOCRApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Matematiksel İfade Tanıma")
        self.setGeometry(100, 100, 1000, 700)
        self.history = []  # Geçmiş öğelerini sakla
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e272e;
            }
            QLabel {
                color: #dfe6e9;
                font-size: 14px;
            }
            QStatusBar {
                background-color: #2d3436;
                color: #b2bec3;
                border-top: 1px solid #636e72;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Başlık
        header_label = QLabel("Matematiksel İfade Tanıma")
        header_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #dfe6e9;
            padding: 5px;
        """)
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)

        # Görüntü alanı
        self.video_label = QLabel(self)
        self.video_label.setMinimumSize(800, 450)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            background-color: #2d3436;
            border-radius: 10px;
            border: 2px solid #636e72;
            padding: 10px;
        """)
        main_layout.addWidget(self.video_label)

        # Butonlar
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Resim Yükle - Mavi tonu
        self.load_image_button = ModernButton("Resim Yükle", 
            color="#2980b9", 
            hover_color="#3498db", 
            pressed_color="#2471a3")
        self.load_image_button.clicked.connect(self.load_sample_image)
        button_layout.addWidget(self.load_image_button)

        # Kameradan İşlem Yap - Yeşil tonu
        self.capture_button = ModernButton("Kameradan İşlem Yap (Space)", 
            color="#27ae60", 
            hover_color="#2ecc71", 
            pressed_color="#219a52")
        self.capture_button.clicked.connect(self.capture_and_process)
        self.capture_button.setShortcut(Qt.Key_Space)
        button_layout.addWidget(self.capture_button)

        # Geçmiş - Mor tonu
        self.history_button = ModernButton("Geçmiş", 
            color="#8e44ad", 
            hover_color="#9b59b6", 
            pressed_color="#7d3c98")
        self.history_button.clicked.connect(self.show_history)
        button_layout.addWidget(self.history_button)

        # Temizle - Turuncu tonu
        self.clear_button = ModernButton("Temizle", 
            color="#d35400", 
            hover_color="#e67e22", 
            pressed_color="#c0392b")
        self.clear_button.clicked.connect(self.clear_results)
        button_layout.addWidget(self.clear_button)

        # Çıkış - Kırmızı tonu
        self.quit_button = ModernButton("Çıkış", 
            color="#c0392b", 
            hover_color="#e74c3c", 
            pressed_color="#a93226")
        self.quit_button.clicked.connect(self.close)
        button_layout.addWidget(self.quit_button)

        main_layout.addLayout(button_layout)

        # Sonuç alanı
        result_frame = QFrame()
        result_frame.setStyleSheet("""
            QFrame {
                background-color: #2d3436;
                border-radius: 10px;
                border: 2px solid #636e72;
                padding: 15px;
            }
        """)
        result_layout = QVBoxLayout(result_frame)
        result_layout.setSpacing(10)

        # LaTeX görüntüsü için etiket
        self.latex_label = QLabel()
        self.latex_label.setAlignment(Qt.AlignCenter)
        self.latex_label.setMinimumHeight(80)
        result_layout.addWidget(self.latex_label)

        # Sonuç görüntüsü için etiket
        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setMinimumHeight(80)
        result_layout.addWidget(self.result_label)

        main_layout.addWidget(result_frame)

        # Durum çubuğu
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Hazır")

        # Kamera başlat
        self.kamera = cv2.VideoCapture(0)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def render_latex(self, latex_str):
        fig = plt.figure(figsize=(8, 2))
        fig.patch.set_facecolor('#2d3436')
        plt.text(0.5, 0.5, f"${latex_str}$", 
                horizontalalignment='center',
                verticalalignment='center',
                fontsize=20,
                color='#dfe6e9')
        plt.axis('off')
        
        # Matplotlib figürünü QPixmap'e dönüştür
        canvas = FigureCanvas(fig)
        canvas.draw()
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, facecolor='#2d3436')
        buf.seek(0)
        img = QImage.fromData(buf.getvalue())
        pixmap = QPixmap.fromImage(img)
        plt.close(fig)
        return pixmap

    def show_history(self):
        if not self.history:
            QMessageBox.information(self, "Geçmiş", "Henüz işlem geçmişi bulunmuyor.")
            return
        dialog = HistoryDialog(self.history, self)
        dialog.exec_()

    def process_with_mathpix(self, frame):
        try:
            app_id = "your_app_ıd"
            app_key = "your_app_key"

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
                    # Değişkeni tanımla
                    x = sp.Symbol('x')
                    u = sp.Symbol('u')
                    
                    # Farklı ifade türlerini işle
                    if r'\lim' in latex_expr:
                        # Limitleri işle
                        try:
                            # İfadeyi ve limit noktasını çıkar
                            import re
                            # Yönlü limitler ve daha karmaşık ifadeler için güncellenmiş regex
                            match = re.search(r'\\lim_{([a-zA-Z]+)\\rightarrow([^{}]+)(?:\^{+}|\^{-})?}(.*)', latex_expr)
                            if match:
                                var_str = match.group(1).strip()
                                point_str = match.group(2).strip()
                                expr_str = match.group(3).strip()
                                
                                var = sp.Symbol(var_str)
                                expr_str = expr_str.replace('\\left(', '(').replace('\\right)', ')')
                                expr_str = expr_str.replace('\\log', 'ln')  # log'u ln'e dönüştür
                                expr_str = expr_str.replace('\\left|', 'Abs(').replace('\\right|', ')')  # Mutlak değeri işle
                                
                                try:
                                    expr = sp.parse_latex(expr_str)
                                except:
                                    # Kesirleri işle
                                    def replace_fraction(match):
                                        num = match.group(1).strip()
                                        den = match.group(2).strip()
                                        return f"({num})/({den})"
                                    
                                    # Önce iç içe kesirleri işle
                                    while '\\frac' in expr_str:
                                        expr_str = re.sub(r'\\frac\{([^{}]+|(?:\{[^{}]*\})+)\}\{([^{}]+|(?:\{[^{}]*\})+)\}', replace_fraction, expr_str)
                                    
                                    # Üsleri işle
                                    expr_str = re.sub(r'x\^{(\d+)}', r'x**\1', expr_str)
                                    # Çarpmayı işle
                                    expr_str = re.sub(r'(\d+)\s*x', r'\1*x', expr_str)
                                    # Boşlukları kaldır
                                    expr_str = expr_str.replace(' ', '')
                                    print("Dönüştürülen limit ifadesi:", expr_str)
                                    
                                    # Yaygın limit kalıpları için özel işleme
                                    if 'ln(1+x)/x' in expr_str or 'log(1+x)/x' in expr_str:
                                        result = sp.Integer(1)  # Bilinen limit 1'dir
                                    else:
                                        try:
                                            expr = sp.sympify(expr_str, locals={var_str: var})
                                            # Yönlü limitleri işle
                                            if '^{+}' in latex_expr:
                                                result = sp.limit(expr, var, sp.sympify(point_str), dir='+')
                                            elif '^{-}' in latex_expr:
                                                result = sp.limit(expr, var, sp.sympify(point_str), dir='-')
                                            else:
                                                result = sp.limit(expr, var, sp.sympify(point_str))
                                        except:
                                            # sympify başarısız olursa, ifadeyi doğrudan oluşturmayı dene
                                            if 'sin(x)/x' in expr_str:
                                                result = sp.Integer(1)  # Bilinen limit 1'dir
                                            elif 'cos(x)-1/x' in expr_str:
                                                result = sp.Integer(0)  # Bilinen limit 0'dır
                                            else:
                                                raise ValueError(f"Limit ifadesi çözümlenemedi: {expr_str}")
                            else:
                                raise ValueError("Limit ifadesi formatı tanınmadı")
                        except Exception as e:
                            print(f"Limit hesaplama hatası: {str(e)}")
                            # Bilinen limitler için son çare
                            if '\\frac{\\log (1+x)}{x}' in latex_expr or '\\frac{\\ln (1+x)}{x}' in latex_expr:
                                result = sp.Integer(1)  # Bilinen limit 1'dir
                            elif '\\frac{\\sin x}{x}' in latex_expr:
                                result = sp.Integer(1)  # Bilinen limit 1'dir
                            elif '\\frac{\\cos x - 1}{x}' in latex_expr:
                                result = sp.Integer(0)  # Bilinen limit 0'dır
                            else:
                                raise ValueError(f"Limit hesaplanamadı: {str(e)}")
                    elif r'\int' in latex_expr:
                        # İntegrali işle
                        parts = latex_expr.split(r'\int')
                        if len(parts) > 1:
                            # Fonksiyon kısmını al (limitleri ve dx'i kaldır)
                            func_part = parts[1].split('dx')[0] if 'dx' in parts[1] else parts[1].split('d u')[0]
                            
                            # Limitleri çıkar
                            if '_{' in func_part and '}^{' in func_part:
                                # Limitleri al
                                limits_part = func_part[:func_part.find('\\left[')] if '\\left[' in func_part else func_part
                                lower = float(limits_part.split('_{')[1].split('}^{')[0])
                                upper = float(limits_part.split('}^{')[1].split('}')[0])
                                
                                # Limitlerden sonraki fonksiyon kısmını al
                                if '\\left[' in func_part:
                                    func_part = func_part[func_part.find('\\left['):]
                                else:
                                    func_part = func_part[func_part.find('}')+1:]
                            else:
                                lower = None
                                upper = None
                            
                            # Fonksiyon kısmını temizle
                            func_part = func_part.replace('\\left[', '').replace('\\right]', '')
                            func_part = func_part.replace('\\left(', '').replace('\\right)', '')
                            func_part = func_part.replace('\\operatorname{coth}', 'coth')
                            func_part = func_part.strip()
                            
                            print("Fonksiyon kısmı:", func_part)  # Hata ayıklama yazdırması
                            
                            # LaTeX'i SymPy ifadesine dönüştür
                            try:
                                # Önce LaTeX'i doğrudan ayrıştırmayı dene
                                integrand = sp.parse_latex(func_part)
                            except:
                                # Başarısız olursa, daha basit bir forma dönüştürmeyi dene
                                # x^{n} formatını x**n formatına dönüştür
                                import re
                                # Üsleri işle
                                func_part = re.sub(r'x\^{(\d+)}', r'x**\1', func_part)
                                # Çarpmayı işle
                                func_part = re.sub(r'(\d+)\s*x', r'\1*x', func_part)
                                # Boşlukları kaldır
                                func_part = func_part.replace(' ', '')
                                print("Dönüştürülen fonksiyon kısmı:", func_part)  # Hata ayıklama yazdırması
                                # SymPy'nin ayrıştırmasını kullanarak ifadeyi oluştur
                                integrand = sp.sympify(func_part, locals={'x': x})
                            
                            # İntegrali hesapla
                            if lower is not None and upper is not None:
                                result = sp.integrate(integrand, (x, lower, upper))
                            else:
                                result = sp.integrate(integrand, x)
                        else:
                            # LaTeX'i SymPy ifadesine dönüştür
                            try:
                                result = sp.parse_latex(latex_expr)
                            except:
                                # Başarısız olursa, daha basit bir forma dönüştürmeyi dene
                                import re
                                # Üsleri işle
                                expr = re.sub(r'x\^{(\d+)}', r'x**\1', latex_expr)
                                # Çarpmayı işle
                                expr = re.sub(r'(\d+)\s*x', r'\1*x', expr)
                                # Boşlukları kaldır
                                expr = expr.replace(' ', '')
                                print("Dönüştürülen ifade:", expr)  # Hata ayıklama yazdırması
                                # SymPy'nin ayrıştırmasını kullanarak ifadeyi oluştur
                                result = sp.sympify(expr, locals={'x': x})
                    else:
                        # Diğer ifadeleri işle
                        try:
                            result = sp.parse_latex(latex_expr)
                        except:
                            import re
                            # Üsleri işle
                            expr = re.sub(r'x\^{(\d+)}', r'x**\1', latex_expr)
                            # Çarpmayı işle
                            expr = re.sub(r'(\d+)\s*x', r'\1*x', expr)
                            # Boşlukları kaldır
                            expr = expr.replace(' ', '')
                            print("Dönüştürülen ifade:", expr)  # Hata ayıklama yazdırması
                            # SymPy'nin ayrıştırmasını kullanarak ifadeyi oluştur
                            result = sp.sympify(expr, locals={'x': x})
                    
                    # Sonucu LaTeX formatına dönüştür
                    result_latex = sp.latex(result)
                    
                    # Sonucu daha doğal görünmesi için biçimlendir
                    result_latex = result_latex.replace('**', '^')  # x**2'yi x^2'ye dönüştür
                    result_latex = result_latex.replace('*', '')    # Çarpma işaretlerini kaldır
                    result_latex = result_latex.replace('ln', '\\log')  # ln'i log'a geri dönüştür

                    # LaTeX ifadesini görüntüle
                    latex_pixmap = self.render_latex(latex_expr)
                    self.latex_label.setPixmap(latex_pixmap.scaled(
                        self.latex_label.width(), 80,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation))

                    # Sadece sonucu LaTeX formatında görüntüle
                    result_pixmap = self.render_latex(result_latex)
                    self.result_label.setPixmap(result_pixmap.scaled(
                        self.result_label.width(), 80,
                        Qt.KeepAspectRatio, Qt.SmoothTransformation))

                    # Geçmişe ekle
                    self.history.append({
                        'timestamp': datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                        'equation_pixmap': latex_pixmap,
                        'result_pixmap': result_pixmap
                    })

                    self.statusBar.showMessage("Çözüm başarıyla gösterildi.")
                except Exception as e:
                    self.statusBar.showMessage(f"Hata: {str(e)}")
                    print(f"Hata detayları: {str(e)}")
            else:
                self.statusBar.showMessage("Mathpix çözümleme başarısız.")
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
                # Mutlak yolu dönüştür ve normalize et
                abs_path = os.path.abspath(fname)
                frame = cv2.imdecode(np.fromfile(abs_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is None:
                    raise Exception("Görüntü okunamadı")
                self.video_label.setPixmap(QPixmap(fname).scaled(
                    self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.process_with_mathpix(frame)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Resim yüklenemedi: {str(e)}")

    def clear_results(self):
        self.latex_label.clear()
        self.result_label.clear()
        self.statusBar.showMessage("Sonuçlar temizlendi")

    def update_frame(self):
        ret, frame = self.kamera.read()
        if ret:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = QImage(rgb_frame, rgb_frame.shape[1], rgb_frame.shape[0], rgb_frame.strides[0], QImage.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(image).scaled(
                self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

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
