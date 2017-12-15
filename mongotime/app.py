from __future__ import absolute_import

from time import sleep, time
from Queue import Queue

import click
from click import echo, style

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from bson import decode_file_iter

from .sampler import Sampler
from .dumper import Dumper
from .reporter import Reporter
from .plugins import load_plugins


DEFAULT_PORT = 2846


def run():
    cli(obj={})  # pylint: disable=unexpected-keyword-arg


@click.group()
@click.pass_context
def cli(ctx):
    pass


@cli.command()
@click.option(
    '--host', default='localhost:27017', help='Location of Mongo host')
@click.option('--interval', '-i', default=100, help='Sampling interval in ms')
@click.option('--duration', '-d', default=0, help='Duration in sec to record')
@click.argument(
    'recording_file', default='recording.mtime', type=click.File('wb'))
@click.pass_context
def record(ctx, recording_file, host, interval, duration):
    # Having a client doesn't mean we succesfully connected, so ask something
    # that'll force it. Also reduce the timeout from the default 30s, to
    # fail fast when trying to connect to the wrong URI.
    client = MongoClient(
        host,
        connectTimeoutMS=5000,
        serverSelectionTimeoutMS=5000)
    try:
        client.is_primary
    except ServerSelectionTimeoutError:
        exit('Failed to connect to Mongo at %s' % host)

    # If that didn't throw an exception, it must have connected, so recreate
    # the client with default timeouts
    client = MongoClient(host)

    sample_queue = Queue(maxsize=100)

    sampler = Sampler(
        client,
        sample_queue,
        interval_sec=float(interval) / 1000)
    sampler.start()

    # Echo to stderr if recording_file is stdout
    errout = recording_file.fileno() == 1

    dumper = Dumper(sample_queue, recording_file)
    dumper.start()

    start = time()
    end = duration and start + duration

    try:
        echo('Sampling Mongo...', err=errout)

        left = end - time()
        while not duration or left > 0:
            sleep(duration and min(left, 3) or 3)
            echo(
                '  %6d samples  %6d ops' % (
                    sampler.num_samples, sampler.num_ops),
                err=errout)
            left = end - time()
    except KeyboardInterrupt:
        echo(err=errout)
        echo(style('Stopping', fg='red'), err=errout)
    else:
        if sampler.num_dropped:
            echo(
                '%s dropped %d / %d (%.2f%%) samples - unable to keep up' % (
                    style('WARNING:', fg='red'),
                    sampler.num_dropped,
                    sampler.num_samples,
                    100.0 * sampler.num_dropped / sampler.num_samples),
                err=errout)

        echo('Finalizing recording of samples', err=errout)

    sampler.stop()
    dumper.stop()


@cli.command()
@click.argument(
    'recording_file',
    default='recording.mtime',
    type=click.File('rb'))
@click.option(
    '--focus',
    metavar='GROUPING',
    help='View values in just this grouping')
@click.option(
    '--top',
    'num_top',
    type=int,
    help='View top N values in groupings, or 0 for all')
@click.option(
    '--grouping',
    'new_groupings',
    type=(unicode, unicode),
    multiple=True,
    metavar='NAME PY_STATEMENT',
    help='Create a grouping from a name and a python statement which when '
         'eval\'d results in the grouping value')
def analyze(recording_file, focus=None, num_top=None, new_groupings=None):
    reporter = Reporter(list(decode_file_iter(recording_file)))

    if new_groupings:
        for new_grouping in new_groupings:
            reporter.add_grouping_from_eval(*new_grouping)

    plugins = load_plugins()
    for grouping_class in plugins['groupings']:
        reporter.add_grouping(grouping_class)

    echo('== Stats ==')
    for stat, val in sorted(reporter.get_stats().items()):
        echo('  %s = %s' % (stat, val))
    echo()

    groupings = dict(reporter.get_groupings())

    # Optionally focus on one grouping
    if focus:
        groupings = {focus: groupings[focus]}
    elif num_top is None:
        # If not explicitly told to show all, default to 5
        num_top = 5

    reporter.print_top(groupings, num_top=num_top)
