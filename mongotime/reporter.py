from collections import defaultdict

from click import echo, style


class Reporter(object):
    """Analyses samples and builds reports.
    """

    def __init__(self, filter_stmt=None):
        if filter_stmt:
            filter_code = compile(filter_stmt, '', 'eval')

            def run_filter(groupings):
                return eval(  # pylint: disable=eval-used
                    filter_code, {}, groupings)

            self._filter = run_filter
        else:
            self._filter = None

        self._plugin_groupings = {}
        self._eval_groupings = {}

        self.report = Report(is_filtered=self._filter is not None)

    def add_grouping(self, grouping_class):
        # Store instance of grouping, not the class
        grouping = grouping_class()
        self._plugin_groupings[grouping.get_name()] = grouping

    def add_grouping_from_eval(self, name, stmnt):
        self._eval_groupings[name] = (
            lambda op, g: eval(  # pylint: disable=eval-used
                stmnt, {'o': op, 'g': g}))

    def add_sample(self, sample_t, ops):
        self.report.sampling_times.add(sample_t)

        if not ops:
            return

        self.report.num_ops += len(ops)
        self.report.active_sampling_times.add(sample_t)

        for op in ops:
            groupings = self._extract_groupings(op)
            if not self._filter or self._filter(groupings):
                self.report.filtered_sampling_times.add(sample_t)

                for name, value in groupings.iteritems():
                    self.report.grouping_values[name][str(value)].add(sample_t)

    def _extract_groupings(self, op):
        # Get builtin groupings first, then pass those to the user ones
        groupings = {
            name: extractor(op)
            for name, extractor in BUILTIN_GROUPINGS.items()
        }

        user_groupings = {}

        # First plugin groupings
        for name, grouping in self._plugin_groupings.iteritems():
            user_groupings[name] = get_grouping_value(
                grouping.get_value, op, groupings)

        # Then cmdline ones
        for name, get_value in self._eval_groupings.iteritems():
            user_groupings[name] = get_grouping_value(
                get_value, op, groupings)

        groupings.update(user_groupings)

        return groupings


BUILTIN_GROUPINGS = {
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


def get_grouping_value(fn, op, groupings):
    try:
        return fn(op, groupings)
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

        # Mapping of grouping name to mapping of grouping value to times seen:
        #   {g: {v: {t1, t2, ...}}}
        self.grouping_values = defaultdict(lambda: defaultdict(set))

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
        grouping_values = self.grouping_values
        if focus:
            grouping_values = {
                name: value_series
                for name, value_series in grouping_values.iteritems()
                if name in focus
            }
        elif num_top is None:
            # If not explicitly told to show all, default to 5
            num_top = 5

        # turn into % time spent in general by comparing # of times seen with
        # # of times sampled
        grouping_times = {
            grouping: {
                value: 100.0 * len(times) / len(self.sampling_times)
                for value, times in value_series.items()
            }
            for grouping, value_series in grouping_values.items()
        }

        # turn into % of active-time spent on each thing
        grouping_active_usage = {
            grouping: {
                value: 100.0 * len(times) / len(self.active_sampling_times)
                for value, times in value_series.items()
            } for grouping, value_series in grouping_values.items()
        }

        # get % of filtered-active time for each thing
        grouping_filtered_usage = {
            grouping: {
                value: 100.0 * len(times) / len(self.filtered_sampling_times)
                for value, times in value_series.items()
            } for grouping, value_series in grouping_values.items()
        }

        for grouping, value_percs in sorted(grouping_times.items()):
            msg = '%s:' % style(grouping, fg='blue')
            if num_top and len(value_percs) > num_top:
                msg = '%s (top %d of %d)' % (msg, num_top, len(value_percs))
            echo(msg)

            top_values = sorted(
                value_percs.items(), key=lambda(v, p): p, reverse=True)

            if num_top:
                top_values = top_values[:num_top]

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

                perc_active_str = '%.2f%%' % (
                    grouping_active_usage[grouping][value])

                line = '  %s: %s %s' % (value, styled_perc, perc_active_str)

                if self.is_filtered:
                    line = '%s %.2f%%' % (
                        line, grouping_filtered_usage[grouping][value])

                echo(line)

            echo()
