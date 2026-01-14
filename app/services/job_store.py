from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class JobStore(ABC):
    @abstractmethod
    def create(self, job_id: str, data: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def update(self, job_id: str, data: Dict[str, Any]) -> None:
        ...

    @abstractmethod
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        ...

    @abstractmethod
    def list(self) -> List[Dict[str, Any]]:
        ...
