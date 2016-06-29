from collections import defaultdict

from click import echo, style


class Reporter(object):
    """Analyses samples and builds reports.
    """

    def __init__(self, samples, query=None):
        self._samples = samples
        self._query = query

        self._feature_extractors = {
            # Passthrough
            'ns': lambda op: op.get('ns') or '',
            'client': lambda op: op.get('client') or '',
            'op': lambda op: op.get('op') or '',
            'query': extract_query,

            'db': lambda op: op.get('ns', '').split('.', 1)[0],
            'collection': lambda op: op.get('ns', '.').split('.', 1)[1],

            'client_host': lambda op: op.get('client', ':').split(':', 1)[0],
        }

    def stats(self):
        echo('== Stats ==')
        for stat, val in sorted(self._samples.stats().items()):
            echo('  %s = %s' % (stat, val))

    def top(self):
        samples = self._samples.select_latest()

        # Extract features for each op
        feature_samples = [
            {
                't': sample['t'],
                'f': [
                    self._extract_features(op)
                    for op in sample['o']
                ]
            }
            for sample in samples
        ]

        # Filter by query
        if self._query:
            try:
                feature_samples = [
                    {
                        't': s['t'],
                        'f': [
                            op_features
                            for op_features in s['f']
                            if matches_query(op_features, self._query)
                        ],
                    }
                    for s in feature_samples
                ]
            except QueryError:
                return

        # Flatten features in each sample
        flat_samples = [
            {
                't': sample['t'],
                'f': dict(reduce(
                    lambda a, b: a | set(b.items()),
                    sample['f'],
                    set())),
            }
            for sample in feature_samples
        ]

        # pivot features/time to feaures->times
        index_by_ts = {s['t']: i for i, s in enumerate(samples)}
        feature_series = defaultdict(
            lambda: defaultdict(lambda: [0]*len(samples)))
        for sample in flat_samples:
            for feature, value in sample['f'].items():
                index = index_by_ts[sample['t']]
                feature_series[feature][value][index] = 1

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

    def _extract_features(self, op):
        return {
            name: extractor(op)
            for name, extractor in self._feature_extractors.items()
        }


def extract_query(op):
    """Extract a hashable value representing the query, with an attempt
    at removing the particular values for keys in the query
    """
    return repr(strip_values(op.get('query')))


KEYS_TO_NOT_STRIP = {
    '$or', '$and', '$not', '$nor',
    '$exists', '$type',
    '$mod', '$regex', '$where',
    '$msg',
}


def strip_values(data):
    if isinstance(data, dict):
        return [
            {key: strip_values(value)} if key in KEYS_TO_NOT_STRIP else key
            for key, value in data.items()
        ]
    elif isinstance(data, list):
        return [strip_values(item) for item in data]
    return data


class QueryError(Exception):
    pass


def matches_query(op_features, query):
    try:
        return eval(query, dict(op_features))
    except Exception as err:
        echo('Error (%s) running query on Op: %s' % (
            style(str(err), fg='red'),
            style(str(op_features), fg='blue')))
        raise QueryError(str(err))
