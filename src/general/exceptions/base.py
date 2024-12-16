from dataclasses import dataclass


@dataclass(eq=False)
class GeneralException(Exception):
    @property
    def message(self) -> str:
        return "Occur exception in general"
