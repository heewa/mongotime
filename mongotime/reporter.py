from collections import defaultdict

from click import echo, style


class Reporter(object):
    """Analyses samples and builds reports.
    """

    def __init__(self, samples):
        self._samples = samples

    def stats(self):
        echo('== Stats ==')
        for stat, val in sorted(self._samples.stats().items()):
            echo('  %s = %s' % (stat, val))

    def top(self):
        samples = self._samples.select_latest()

        # pivot features/time to feaures->times
        index_by_ts = {s['t']: i for i, s in enumerate(samples)}
        feature_series = defaultdict(
            lambda: defaultdict(lambda: [0]*len(samples)))
        for sample in samples:
            for op in sample['o']:
                for feature, value in op.items():
                    index = index_by_ts[sample['t']]
                    feature_series[feature][str(value)][index] = 1

        # turn into % time spent
        feature_times = {
            feature: {
                value: 100.0 * sum(series) / len(series)
                for value, series in value_series.items()
            }
            for feature, value_series in feature_series.items()
        }

        for feature, value_percs in sorted(feature_times.items()):
            echo('%s:' % style(feature, fg='blue'))

            top_values = sorted(
                value_percs.items(), key=lambda(v, p): p, reverse=True)[:5]
            for value, perc in top_values:
                perc_str = '%.2f%%' % perc
                if perc >= 80:
                    styled_perc = style(perc_str, fg='red', bold=True)
                elif perc >= 30:
                    styled_perc = style(perc_str, fg='yellow', bold=True)
                elif perc >= 8:
                    styled_perc = style(perc_str, bold=True)
                else:
                    styled_perc = perc_str
                echo('  %s: %s' % (value, styled_perc))

            echo()
