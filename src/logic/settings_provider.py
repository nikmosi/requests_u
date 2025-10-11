from abc import ABC, abstractmethod

from config.data import Settings


class SettingsProvider(ABC):
    @abstractmethod
    def get(self) -> Settings: ...
