import time
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
        self.tool_id  = tool_id
        self.token    = token
        self._stopped = False

    def stop(self):
        self._stopped = True

    def run(self):
        deadline = time.time() + POLL_TIMEOUT
        while not self._stopped and time.time() < deadline:
            decision = alert_sender.poll_approval(self.token)
            if decision == "approve":
                self.decided.emit(self.tool_id, True)
                return
            if decision == "reject":
                self.decided.emit(self.tool_id, False)
                return
            time.sleep(POLL_INTERVAL)
        # Timeout sin respuesta → rechazar por defecto
        if not self._stopped:
            self.decided.emit(self.tool_id, False)
