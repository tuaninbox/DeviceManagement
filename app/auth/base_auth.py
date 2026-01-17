from abc import ABC, abstractmethod

class AuthProvider(ABC):
    @abstractmethod
    def authenticate(self, username: str, password: str):
        pass
