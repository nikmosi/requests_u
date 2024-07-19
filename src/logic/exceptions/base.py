from dataclasses import dataclass


@dataclass
class LogicException(Exception):
    @property
    def message(self):
        return "Occur error in logic"
