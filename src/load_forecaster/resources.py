"""Sample RSS (including subprocesses) while timing each pipeline stage."""
import threading
import time
from contextlib import contextmanager

import psutil


class ResourceRecorder:
    def __init__(self):
        self.rows = []

    @contextmanager
    def stage(self, name):
        stop = threading.Event()
        proc = psutil.Process()
        peak = [0]

        def sample():
            while True:
                try:
                    processes = [proc] + proc.children(recursive=True)
                    peak[0] = max(peak[0], sum(p.memory_info().rss for p in processes if p.is_running()))
                except psutil.Error:
                    pass
                if stop.wait(0.05):
                    break

        thread = threading.Thread(target=sample, daemon=True)
        start = time.perf_counter()
        thread.start()
        try:
            yield
        finally:
            stop.set()
            thread.join()
            self.rows.append({"stage": name, "seconds": time.perf_counter() - start, "peak_rss_mb": peak[0] / 1024 ** 2})
