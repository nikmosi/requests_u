from dataclasses import dataclass


@dataclass(eq=False)
class BaseDomainError(Exception):
    @property
    def message(self):
        return "Occur exception in domain"
