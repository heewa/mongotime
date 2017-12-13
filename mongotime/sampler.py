from time import time, sleep
from Queue import Full

from .thread_with_stop import ThreadWithStop


class Sampler(ThreadWithStop):
    """Samples the DB for Ops at a regular interval
    """

    def __init__(self, db, sample_queue, interval_sec=0.100):
        super(Sampler, self).__init__(name='Sampler')

        self._db = db
        self._sample_queue = sample_queue
        self._interval_sec = interval_sec
        self._client_id = None

        # Some stats
        self.num_samples = 0
        self.num_ops = 0
        self.num_dropped = 0

    def _run(self):
        # Get our client ID so we can exclude our own sampling Ops
        self._client_id = self._db.admin.command('whatsmyuri')['you']

        while not self._stop.is_set():
            tick_start = time()

            sample = self._take_sample()
            self.num_samples += 1
            self.num_ops += len(sample['o'])

            try:
                self._sample_queue.put(sample, block=False)
            except Full:
                # Keep stats on dropped samples
                self.num_dropped += 1

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

        # Filter for keys we're interested in, and remove empty ones. Also
        # remove our own Ops
        ops = [
            {key: value for key, value in op.iteritems() if value}
            for op in result['inprog']
            if not (
                op.get('client') == self._client_id and
                op.get('ns') == 'admin.$cmd')
        ]

        return {'t': timestamp, 'o': ops}
