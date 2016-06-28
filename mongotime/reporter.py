from click import echo


class Reporter(object):
    """Analyses samples and builds reports.
    """

    def __init__(self, samples):
        self._samples = samples

    def stats(self):
        echo('== Stats ==')
        for stat, val in sorted(self._samples.stats().items()):
            echo('  %s = %s' % (stat, val))
