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
def cli():
    pass


@cli.command()
@click.option(
    '--host', default='localhost:27017', help='Location of Mongo host')
@click.option('--interval', '-i', default=100, help='Sampling interval in ms')
@click.option('--duration', '-d', default=0, help='Duration in sec to record')
@click.argument(
    'recording_file', default='recording.mtime', type=click.File('wb'))
def record(recording_file, host, interval, duration):
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
    metavar='ASPECT',
    help='View items in just this aspect (category of activity)')
@click.option(
    '--top',
    'num_top',
    type=int,
    help='View top N values in aspects, or 0 for all')
@click.option(
    '--aspect',
    'new_aspects',
    type=(unicode, unicode),
    multiple=True,
    metavar='NAME PY_STATEMENT',
    help='Create an aspect from a name and a python statement which when '
         'eval\'d results in the aspect value')
@click.option(
    '--filter',
    'filter_stmt',
    metavar='PY_STATEMENT',
    help='Filter ops by this python statement returning True')
def analyze(
        recording_file,
        focus=None,
        num_top=None,
        new_aspects=None,
        filter_stmt=None):
    # Set up reporter
    reporter = Reporter(filter_stmt=filter_stmt)

    if new_aspects:
        for new_aspect in new_aspects:
            reporter.add_aspect_from_eval(*new_aspect)

    plugins = load_plugins()
    for aspect_class in plugins['aspects']:
        reporter.add_aspect(aspect_class)

    # Stream samples to reporter
    for sample in decode_file_iter(recording_file):
        reporter.add_sample(sample['t'], sample['o'])

    echo('== Summary ==')
    for stat, val in sorted(reporter.report.get_summary().items()):
        echo('  %s = %s' % (stat, val))
    echo()

    reporter.report.print_top(focus=focus, num_top=num_top)
