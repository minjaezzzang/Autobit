import sys
import pickle
import datetime as dt
import logging as lg
import socket
import os
from functools import partial
from concurrent.futures import ThreadPoolExecutor
import pyupbit as pu
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QLineEdit, QMessageBox,
    QPlainTextEdit, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QPalette, QColor

# 로깅 설정
lg.basicConfig(level=lg.INFO,
               format='%(asctime)s | %(levelname)s | %(message)s',
               filename='autobit.log',
               filemode='w')

# 전략 함수 - numba 없이 순수 파이썬
def compute_drop(ref_price, current_price):
    return (ref_price - current_price) / ref_price if ref_price else 0.0

def compute_change(start_price, end_price):
    return (end_price - start_price) / start_price if start_price else 0.0

class NetworkChecker(QObject):
    status_changed = pyqtSignal(bool)

    def __init__(self, interval=3000):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self.check)
        self.timer.start(interval)

    def check(self):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=1).close()
            self.status_changed.emit(True)
        except:
            self.status_changed.emit(False)

class UpbitWorker(QObject):
    price_updated = pyqtSignal(float)
    balance_updated = pyqtSignal(dict)

    def __init__(self, upbit, interval_price=8000, interval_bal=25000):
        super().__init__()
        self.upbit = upbit
        self.timer_price = QTimer()
        self.timer_price.timeout.connect(self.fetch_price)
        self.timer_price.start(interval_price)
        self.timer_bal = QTimer()
        self.timer_bal.timeout.connect(self.fetch_balance)
        self.timer_bal.start(interval_bal)

    def fetch_price(self):
        try:
            price = pu.get_current_price("KRW-BTC") or 0.0
            self.price_updated.emit(price)
        except Exception as e:
            lg.error(f"Price fetch failed: {e}")

    def fetch_balance(self):
        try:
            krw = self.upbit.get_balance("KRW") or 0
            btc = self.upbit.get_balance("BTC") or 0
            self.balance_updated.emit({'KRW': krw, 'BTC': btc})
        except Exception as e:
            lg.error(f"Balance fetch failed: {e}")

class TradingThread(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self, upbit, get_strategy):
        super().__init__()
        self.upbit = upbit
        self.get_strategy = get_strategy
        self.running = False
        self.ref_price = 0.0
        self.prices = []
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count())

    def run(self):
        self.running = True
        while self.running:
            try:
                price = pu.get_current_price("KRW-BTC") or 0.0
                bal = {
                    'KRW': self.upbit.get_balance("KRW") or 0,
                    'BTC': self.upbit.get_balance("BTC") or 0
                }
                strat = self.get_strategy() or ""
                drop = compute_drop(self.ref_price, price)
                change = 0.0

                if strat == "공격적":
                    if self.ref_price == 0.0:
                        self.ref_price = price
                    if drop >= 0.01 and bal['KRW'] > 10000:
                        amt = bal['KRW'] * 0.5 * 0.995
                        try:
                            self.upbit.buy_market_order("KRW-BTC", amt)
                            self.log_signal.emit(f"[공격적] 매수: {amt:,.0f} KRW")
                        except Exception as e:
                            self.log_signal.emit(f"[공격적] 매수 오류: {e}")
                    self.ref_price = price

                elif strat == "안전":
                    self.prices.append(price)
                    if len(self.prices) > 30:
                        start = self.prices.pop(0)
                        change = compute_change(start, price)
                        if change >= 0.003 and bal['BTC'] > 0.0001:
                            try:
                                self.upbit.sell_market_order("KRW-BTC", bal['BTC'] * 0.995)
                                self.log_signal.emit(f"[안전] 매도: {bal['BTC']:.4f} BTC")
                            except Exception as e:
                                self.log_signal.emit(f"[안전] 매도 오류: {e}")

                elif strat == "균형":
                    if self.ref_price == 0.0:
                        self.ref_price = price
                    change = -compute_drop(self.ref_price, price)
                    if change >= 0.01 and bal['BTC'] > 0.0001:
                        try:
                            self.upbit.sell_market_order("KRW-BTC", bal['BTC'] * 0.3 * 0.995)
                            self.log_signal.emit("[균형] 상승 매도")
                        except Exception as e:
                            self.log_signal.emit(f"[균형] 매도 오류: {e}")
                        self.ref_price = price
                    elif change <= -0.01 and bal['KRW'] > 10000:
                        try:
                            self.upbit.buy_market_order("KRW-BTC", bal['KRW'] * 0.3 * 0.995)
                            self.log_signal.emit("[균형] 하락 매수")
                        except Exception as e:
                            self.log_signal.emit(f"[균형] 매수 오류: {e}")
                        self.ref_price = price

                self.msleep(10000)  # 10초 대기
            except Exception as e:
                self.log_signal.emit(f"트레이드 루프 오류: {e}")
                self.msleep(5000)
        self.executor.shutdown()

    def stop(self):
        self.running = False
        self.wait()

class TradingGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("모던 암호화폐 자동거래")
        self.resize(960, 700)
        self.upbit = None
        self.trader = None
        self.current_strategy = "안전"
        self.init_ui()
        self.network_checker = NetworkChecker()
        self.network_checker.status_changed.connect(self.update_network_label)

    def init_ui(self):
        self.net_label = QLabel("네트워크: 확인 중")
        self.status_label = QLabel("상태: 대기중")
        self.price_label = QLabel("BTC 현재가: -- KRW")
        self.balance_label = QLabel("잔액: --")
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("API Key")
        self.sec_input = QLineEdit()
        self.sec_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.sec_input.setPlaceholderText("API Secret")

        self.connect_btn = QPushButton("API 연결")
        self.connect_btn.clicked.connect(self.test_connection)
        self.save_btn = QPushButton("설정 저장")
        self.save_btn.clicked.connect(self.save_settings)
        self.start_btn = QPushButton("거래 시작")
        self.start_btn.clicked.connect(self.start_trading)
        self.stop_btn = QPushButton("거래 중지")
        self.stop_btn.clicked.connect(self.stop_trading)
        self.stop_btn.setEnabled(False)

        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems(["공격적", "안전", "균형"])
        self.strategy_combo.setCurrentText(self.current_strategy)
        self.strategy_combo.currentTextChanged.connect(self.set_strategy)

        top = QHBoxLayout()
        top.addWidget(self.net_label)
        top.addStretch()
        top.addWidget(self.status_label)

        api_layout = QHBoxLayout()
        api_layout.addWidget(self.key_input)
        api_layout.addWidget(self.sec_input)
        api_layout.addWidget(self.connect_btn)
        api_layout.addWidget(self.save_btn)

        info_layout = QHBoxLayout()
        info_layout.addWidget(self.price_label)
        info_layout.addWidget(self.balance_label)
        info_layout.addWidget(QLabel("전략:"))
        info_layout.addWidget(self.strategy_combo)
        info_layout.addStretch()

        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.stop_btn)

        main = QVBoxLayout(self)
        main.addLayout(top)
        main.addLayout(api_layout)
        main.addLayout(info_layout)
        main.addLayout(ctrl_layout)
        main.addWidget(self.log_area)

        self.apply_dark_mode()

    def apply_dark_mode(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(40, 40, 40))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(50, 50, 50))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Highlight, QColor(80, 160, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        QApplication.instance().setPalette(palette)

    def update_network_label(self, ok):
        self.net_label.setText("네트워크: 연결됨" if ok else "네트워크: 끊김")

    def test_connection(self):
        key, sec = self.key_input.text().strip(), self.sec_input.text().strip()
        if not key or not sec:
            QMessageBox.warning(self, "경고", "API 키와 시크릿을 입력하세요.")
            return
        try:
            self.upbit = pu.Upbit(key, sec)
            worker = UpbitWorker(self.upbit)
            worker.price_updated.connect(lambda p: self.price_label.setText(f"BTC 현재가: {p:,.0f} KRW"))
            worker.balance_updated.connect(lambda b: self.balance_label.setText(f"잔액: KRW {b['KRW']:,.0f}, BTC {b['BTC']:.6f}"))
            self.status_label.setText("상태: API 연결됨")
            self.start_btn.setEnabled(True)
        except Exception as e:
            lg.error(f"Connection error: {e}")
            self.status_label.setText("상태: 연결 실패")
            QMessageBox.critical(self, "오류", f"API 연결 실패:\n{e}")

    def save_settings(self):
        try:
            data = {'key': self.key_input.text(), 'secret': self.sec_input.text(), 'saved': dt.datetime.now().isoformat()}
            with open('cfg.dat', 'wb') as f:
                pickle.dump(data, f)
            QMessageBox.information(self, "알림", "설정이 저장되었습니다.")
        except Exception as e:
            lg.error(f"Settings save error: {e}")
            QMessageBox.critical(self, "오류", f"설정 저장 실패:\n{e}")

    def start_trading(self):
        if not self.upbit:
            QMessageBox.warning(self, "경고", "API 연결 후 시작하세요.")
            return
        if hasattr(self, 'trader') and self.trader.isRunning():
            return
        self.trader = TradingThread(self.upbit, lambda: self.current_strategy)
        self.trader.log_signal.connect(self.log_area.appendPlainText)
        self.trader.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("상태: 거래 중")

    def stop_trading(self):
        if hasattr(self, 'trader'):
            self.trader.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("상태: 대기중")

    def set_strategy(self, strategy):
        self.current_strategy = strategy
        self.log_area.appendPlainText(f"모드 지정: {strategy}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = TradingGUI()
    gui.show()
    sys.exit(app.exec())
