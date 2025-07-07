from functools import wraps
from typing import Callable

from langchain_core.runnables import Runnable

def one_graph_decorator(func: Callable[[], Runnable]) -> Callable[[], Runnable]:
    storage = {}
    @wraps(func)
    def wrapper() -> Runnable:
        try:
            return storage[func]
        except KeyError:
            storage.setdefault(func, func())
        return storage[func]
    return wrapper
