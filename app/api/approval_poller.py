import time, threading
from PySide6.QtCore import QThread, Signal
from app.api import alert_sender

POLL_INTERVAL = 2   # segundos entre consultas
POLL_TIMEOUT  = 300 # segundos máximo de espera


class ApprovalPoller(QThread):
    """
    Corre en background mientras espera que el usuario responda
    desde el móvil. Cuando llega la decisión emite `decided`.
    """
    decided = Signal(str, bool)   # tool_id, approved

    def __init__(self, tool_id: str, token: str):
        super().__init__()
        self.tool_id    = tool_id
        self.token      = token
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def run(self):
        deadline = time.time() + POLL_TIMEOUT
        while not self._stop_event.is_set() and time.time() < deadline:
            decision = alert_sender.poll_approval(self.token)
            if decision == "approve":
                self.decided.emit(self.tool_id, True)
                return
            if decision == "reject":
                self.decided.emit(self.tool_id, False)
                return
            self._stop_event.wait(POLL_INTERVAL)  # interruptible sleep
        # Timeout sin respuesta → rechazar por defecto
        if not self._stop_event.is_set():
            self.decided.emit(self.tool_id, False)
