# pylint: disable=no-self-use

from unittest import TestCase
from Queue import Queue

from mongotime.sampler import Sampler


class MockDB(object):
    def __init__(self, samples=None, loop=False, client_id=None):
        if not samples:
            self.samples = []
        elif isinstance(samples, int):
            self.samples = [[{'i': str(i)}] for i in range(samples)]
        elif isinstance(samples, list):
            self.samples = samples
        else:
            raise TypeError(samples)

        self.loop = loop
        self.client_id = client_id

    @property
    def admin(self):
        return self

    def command(self, cmd):
        if cmd != 'whatsmyuri':
            raise NotImplementedError
        return {'you': self.client_id}

    def current_op(self):
        if not self.samples:
            sample = []
        else:
            sample = self.samples.pop(0)
            if self.loop:
                self.samples.append(sample)

        return {'inprog': sample}


class TestSampler(TestCase):
    """Test Sample class independent of actuall sampling of the DB
    """
    def run_samples(self, samples=None):
        """Helper to make a sampler, mock db, queue, and run the samples
        through, and wait for smapler to finish. Returns array of samples
        taken.
        """
        db = MockDB(samples)
        queue = Queue(maxsize=len(db.samples))
        sampler = Sampler(
            db,
            queue,
            interval_sec=0,
            max_samples=len(db.samples))

        sampler.start()
        sampler.join()

        samples = []
        while not queue.empty():
            samples.append(queue.get())
        return samples

    def test_initial_stats(self):
        sampler = Sampler(None, None)
        assert sampler.num_samples == 0
        assert sampler.num_ops == 0
        assert sampler.num_dropped == 0

    def test_stop(self):
        sampler = Sampler(MockDB(), Queue(), interval_sec=0)
        sampler.start()
        sampler.stop()

    def test_max_samples(self):
        sampler = Sampler(MockDB(), Queue(), interval_sec=0, max_samples=2)
        sampler.start()
        sampler.join()

    def test_queue(self):
        num = 5
        samples = self.run_samples(num)
        assert len(samples) == num
        for i, sample in enumerate(samples):
            assert len(sample['o']) == 1
            assert sample['o'][0] == {'i': str(i)}
