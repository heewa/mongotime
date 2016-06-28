from threading import Thread, Event
from Queue import Empty

from bson import BSON


class Dumper(Thread):
    """Writes samples to a file
    """

    def __init__(self, sample_queue, dumpfile):
        super(Dumper, self).__init__(name='Dumper')

        self._dumpfile = dumpfile
        self._sample_queue = sample_queue
        self._stop = Event()
        self._stop.set()

    def stop(self):
        if self._stop.is_set():
            raise RuntimeError('Dumper is already stopped')
        self._stop.set()
        self.join()

    def run(self):
        self._stop.clear()
        try:
            self._run_loop()
        finally:
            self._stop.clear()

        self._dumpfile.flush()

    def _run_loop(self):
        while not self._stop.is_set():
            try:
                sample = self._sample_queue.get(block=True, timeout=1)
                self._dumpfile.write(BSON.encode(sample))
            except Empty:
                pass
