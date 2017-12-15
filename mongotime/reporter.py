from collections import defaultdict

from click import echo, style


class Reporter(object):
    """Analyses samples and builds reports.
    """

    def __init__(self, filter_stmt=None):
        if filter_stmt:
            filter_code = compile(filter_stmt, '', 'eval')

            def run_filter(aspects):
                return eval(  # pylint: disable=eval-used
                    filter_code, {}, aspects)

            self._filter = run_filter
        else:
            self._filter = None

        self._plugin_aspects = {}
        self._eval_aspects = {}

        self.report = Report(is_filtered=self._filter is not None)

    def add_aspect(self, aspect_class):
        # Store instance of aspect, not the class
        aspect = aspect_class()
        self._plugin_aspects[aspect.get_name()] = aspect

    def add_aspect_from_eval(self, name, stmnt):
        self._eval_aspects[name] = (
            lambda op, g: eval(  # pylint: disable=eval-used
                stmnt, {'o': op, 'g': g}))

    def add_sample(self, sample_t, ops):
        self.report.sampling_times.add(sample_t)

        if not ops:
            return

        self.report.num_ops += len(ops)
        self.report.active_sampling_times.add(sample_t)

        for op in ops:
            aspects = self._extract_aspects(op)
            if not self._filter or self._filter(aspects):
                self.report.filtered_sampling_times.add(sample_t)

                for name, value in aspects.iteritems():
                    self.report.aspect_values[name][str(value)].add(sample_t)

    def _extract_aspects(self, op):
        # Get builtin aspects first, then pass those to the user ones
        aspects = {
            name: extractor(op)
            for name, extractor in BUILTIN_ASPECTS.items()
        }

        user_aspects = {}

        # First plugin aspects
        for name, aspect in self._plugin_aspects.iteritems():
            user_aspects[name] = get_aspect_value(
                aspect.get_value, op, aspects)

        # Then cmdline ones
        for name, get_value in self._eval_aspects.iteritems():
            user_aspects[name] = get_aspect_value(
                get_value, op, aspects)

        aspects.update(user_aspects)

        return aspects


BUILTIN_ASPECTS = {
    # Passthrough
    'ns': lambda op: op.get('ns'),
    'client': lambda op: op.get('client'),
    'op': lambda op: op.get('op'),

    'query': lambda op: repr(extract_query(op)),
    'query_keys': lambda op: repr(strip_query(extract_query(op))),

    'db': lambda op: op.get('ns', '').split('.', 1)[0],
    'collection': lambda op: op.get('ns', '.').split('.', 1)[1],

    'client_host': lambda op: op.get('client', ':').split(':', 1)[0],

    # The whole op, as a way of seeing a sampling of them
    'raw': str,
}


def extract_query(op):
    """Extract a hashable value representing the query, with an attempt
    at removing the particular values for keys in the query
    """
    if not op.get('query') or op.get('op') not in ('query', 'getmore'):
        return None
    elif isinstance(op['query'], (str, unicode)):
        return op['query']
    elif 'filter' in op['query']:
        return op['query']['filter']
    elif 'find' in op['query']:
        # Empty find
        return {}
    return op['query']


KEYS_TO_NOT_STRIP = {
    '$or', '$and', '$not', '$nor',
    '$exists', '$type',
    '$mod', '$regex', '$where',
    '$msg',
}


def strip_query(data):
    if isinstance(data, dict):
        return {
            key: strip_query(value) if key in KEYS_TO_NOT_STRIP else '*'
            for key, value in sorted(data.items())
        }
    elif isinstance(data, list):
        return [strip_query(item) for item in sorted(data)]
    return data


def get_aspect_value(fn, op, aspects):
    try:
        return fn(op, aspects)
    except Exception as err:  # pylint: disable=broad-except
        # Catching all exceptions here in order to continue with report
        # while showing user the error (and how much it happened)
        return '%s - %s' % (style(type(err).__name__, fg='red'), err)


class Report(object):
    def __init__(self, is_filtered):
        self.is_filtered = is_filtered

        self.num_ops = 0

        # Set of all times Mongo was sampled
        self.sampling_times = set()

        # Set of times Mongo was sampled with some ops
        self.active_sampling_times = set()

        # Set of times Mongo was sampled with filtered ops
        self.filtered_sampling_times = set()

        # Mapping of aspect name to mapping of aspect value to times seen:
        #   {g: {v: {t1, t2, ...}}}
        self.aspect_values = defaultdict(lambda: defaultdict(set))

    def get_summary(self):
        summary = {
            'num_samples': len(self.sampling_times),
            'num_ops': self.num_ops,
            'earliest': min(self.sampling_times),
            'latest': max(self.sampling_times),
        }

        if self.sampling_times:
            span = summary['latest'] - summary['earliest']
            summary['samples_per_sec'] = summary['num_samples'] / span
            summary['perc_active'] = (
                100.0 * len(self.active_sampling_times) /
                len(self.sampling_times))

        if self.is_filtered:
            summary['perc_active_filtered'] = (
                100.0 * len(self.filtered_sampling_times) /
                len(self.sampling_times))

        return summary

    def print_top(self, focus=None, num_top=None):
        aspect_values = self.aspect_values
        if focus:
            aspect_values = {
                name: times_by_value
                for name, times_by_value in aspect_values.iteritems()
                if name in focus
            }
        elif num_top is None:
            # If not explicitly told to show all, default to 5
            num_top = 5

        # Display guide
        if aspect_values:
            echo('%s%%-of-active-time  %%-of-time' % (
                '%-of-filtered-time  ' if self.is_filtered else ''))
            echo()

        for name, times_by_value in sorted(aspect_values.items()):
            msg = '%s:' % style(name, fg='blue')
            if num_top and len(times_by_value) > num_top:
                msg = '%s (top %d of %d)' % (msg, num_top, len(times_by_value))
            echo(msg)

            top_times_by_value = sorted(
                times_by_value.iteritems(),
                key=lambda (v, t): len(t),
                reverse=True)

            if num_top:
                top_times_by_value = top_times_by_value[:num_top]

            for value, times in top_times_by_value:
                num_times = len(times)

                echo('  %s %s %s - %s' % (
                    style_perc(
                        100.0 * num_times / len(self.filtered_sampling_times),
                        color=False) if self.is_filtered else '',
                    style_perc(
                        100.0 * num_times / len(self.active_sampling_times),
                        color=False),
                    style_perc(100.0 * num_times / len(self.sampling_times)),
                    value))

            echo()


def style_perc(perc, color=True):
    perc_str = '{:6.2f}%'.format(perc)

    if not color or perc < 10:
        return perc_str
    elif perc < 50:
        return style(perc_str, bold=True)
    elif perc < 80:
        return style(perc_str, fg='yellow', bold=True)
    return style(perc_str, fg='red', bold=True)
