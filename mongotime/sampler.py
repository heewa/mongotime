from time import time, sleep
from Queue import Full

from .thread_with_stop import ThreadWithStop


def take_sample(db, client_id, include_all=False):
    # Note: get the timestamp _after_ the cmd returns from Mongo, which
    # is probably closed to the time of the sample.
    result = db.admin.current_op(include_all=include_all)
    timestamp = time()

    # Filter for keys we're interested in, and remove empty ones. Also
    # remove our own Ops
    ops = [
        {key: value for key, value in op.iteritems() if value}
        for op in result['inprog']
        if not (
            op.get('client') == client_id and
            op.get('ns') == 'admin.$cmd')
    ]

    return {'t': timestamp, 'o': ops}


class Sampler(ThreadWithStop):
    """Samples the DB for Ops at a regular interval
    """

    def __init__(self, db, sample_queue, interval_sec=0.100, max_samples=None):
        super(Sampler, self).__init__(name='Sampler')

        self._db = db
        self._sample_queue = sample_queue
        self._interval_sec = interval_sec
        self._max_samples = max_samples

        # Some stats
        self.num_samples = 0
        self.num_ops = 0
        self.num_dropped = 0

    def _done(self):
        return (
            self.num_samples >= self._max_samples if self._max_samples
            else self._stop.is_set())

    def _run(self):
        # Get our client ID so we can exclude our own sampling Ops
        client_id = self._db.admin.command('whatsmyuri')['you']

        while not self._done():
            tick_start = time()

            sample = take_sample(self._db, client_id)
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
