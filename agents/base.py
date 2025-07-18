
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    @abstractmethod
    def run(self, input_text: str, session_id: str) -> str:
        pass
