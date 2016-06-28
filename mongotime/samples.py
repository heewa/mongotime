from bson import decode_file_iter


class Samples(object):
    def stats(self):
        raise NotImplementedError

    def select_latest(self, dur=None):
        raise NotImplementedError

    def select_range(self, start, end):
        raise NotImplementedError


class DumpedSamples(Samples):
    def __init__(self, dumpfile):
        self._samples = list(decode_file_iter(dumpfile))

    def stats(self):
        if not self._samples:
            return {'num': 0}

        stats = {
            'num_samples': len(self._samples),
            'num_ops': sum(len(s['o']) for s in self._samples),
            'earliest': self._samples[0]['t'],
            'latest': self._samples[-1]['t'],
        }

        span = stats['latest'] - stats['earliest']
        stats['samples_per_sec'] = stats['num_samples'] / span

        return stats

    def select_latest(self, dur=None):
        if dur:
            raise NotImplementedError

        return self._samples


class ServedSamples(Samples):
    def __init__(self, host, port):
        pass
