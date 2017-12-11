from Queue import Empty

from bson import BSON

from .thread_with_stop import ThreadWithStop


class Dumper(ThreadWithStop):
    """Writes samples to a file
    """

    def __init__(self, sample_queue, dumpfile):
        super(Dumper, self).__init__(name='Dumper')

        self._dumpfile = dumpfile
        self._sample_queue = sample_queue

    def _run(self):
        while not self._stop.is_set():
            try:
                sample = self._sample_queue.get(block=True, timeout=1)
                self._dumpfile.write(BSON.encode(sample))
            except Empty:
                pass

        self._dumpfile.flush()
