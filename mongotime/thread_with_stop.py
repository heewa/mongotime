from threading import Thread, Event


class ThreadWithStop(Thread):
    """Thread with stop functionality, and a flag to check in a run loop
    """

    def __init__(self, *args, **kwargs):
        super(ThreadWithStop, self).__init__(*args, **kwargs)

        self._stop = Event()
        self._stop.set()

    def stop(self):
        """Set stop flag so run loop will exit at next chance, and wait
        """
        if self._stop.is_set():
            raise RuntimeError('Dumper is already stopped')
        self._stop.set()
        self.join()

    def run(self):
        self._stop.clear()
        try:
            self._run()
        finally:
            self._stop.clear()
