from abc import ABC, abstractmethod
from PySide6.QtGui import QPainter


class Background(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def render(self, painter: QPainter, width: int, height: int, t: float):
        """Render the background at time t (seconds)."""
        pass

    def get_default_settings(self) -> dict:
        return {}
