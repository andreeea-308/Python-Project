import logging
from queue import Queue
from threading import Thread
from typing import Any, Callable, Dict

from ..exceptions.handlers import handle_generic_exception

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MathWorker(Thread):
    def __init__(self, task_queue: Queue):
        super().__init__(daemon=True)
        self.queue = task_queue

    def run(self):
        while True:
            task = self.queue.get()
            if task is None:
                logger.info("Worker oprit (exit signal primit).")
                break

            try:
                func: Callable = task["func"]
                args: Dict[str, Any] = task["args"]
                callback: Callable = task.get("callback", lambda *_: None)

                logger.debug(f"Pornesc task: {func.__name__}({args})")
                result = func(**args)
                callback(result)
                logger.debug(f"Task completat: {func.__name__}")
            except Exception as e:
                handle_generic_exception(e, context="Eroare în worker")
            finally:
                self.queue.task_done()
