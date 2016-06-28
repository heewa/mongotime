from time import time, sleep
from threading import Thread, Event
from Queue import Full


"""Keys to keep from sampled Ops
"""
OP_KEYS = {
    'client', 'desc', 'locks', 'ns', 'op', 'query', 'microsecs_running',
    'waiting_for_lock',
}


class Sampler(Thread):
    """Samples the DB for Ops at a regular interval
    """

    def __init__(self, db, sample_queue, interval_sec=0.100):
        super(Sampler, self).__init__(name='Sampler')

        self._db = db
        self._sample_queue = sample_queue
        self._interval_sec = interval_sec
        self._stop = Event()
        self._stop.set()

    def stop(self):
        if self._stop.is_set():
            raise RuntimeError('Sampler is already stopped')
        self._stop.set()
        self.join()

    def run(self):
        self._stop.clear()
        try:
            self._run_loop()
        finally:
            self._stop.clear()

    def _run_loop(self):
        while not self._stop.is_set():
            tick_start = time()

            sample = self._take_sample()

            try:
                self._sample_queue.put(sample, block=False)
            except Full:
                # TODO: keep stats on dropped samples
                pass

            # Sleep for remaining time. It's ok if we under-sample, but don't
            # go over.
            remainder = self._interval_sec - (time() - tick_start)
            if remainder > 0:
                sleep(remainder)

    def _take_sample(self):
        # Note: get the timestamp _after_ the cmd returns from Mongo, which
        # is probably closed to the time of the sample.
        result = self._db.admin.current_op()
        timestamp = time()

        # Filter for keys we're interested in, and remove empty ones
        ops = [
            dict(
                (key, value)
                for key, value in op.items()
                if value and key in OP_KEYS
            )
            for op in result['inprog']
        ]

        return {'t': timestamp, 'o': ops}
