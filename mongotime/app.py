from __future__ import absolute_import

from time import sleep, time
from Queue import Queue

import click
from click import echo, style

from pymongo import MongoClient
from bson import decode_file_iter

from .sampler import Sampler
from .dumper import Dumper
from .reporter import Reporter


DEFAULT_PORT = 2846


def run():
    cli(obj={})  # pylint: disable=unexpected-keyword-arg


@click.group()
@click.option('--db', default='localhost:27017', help='Location of Mongo host')
@click.pass_context
def cli(ctx, db):
    ctx.obj['db'] = MongoClient(db)


@cli.command()
@click.option('--interval', '-i', default=100, help='Sampling interval in ms')
@click.option('--duration', '-d', default=0, help='Duration in sec to record')
@click.argument(
    'recording_file', default='recording.mtime', type=click.File('wb'))
@click.pass_context
def record(ctx, recording_file, interval, duration):
    sample_queue = Queue(maxsize=100)

    sampler = Sampler(
        ctx.obj['db'],
        sample_queue,
        interval_sec=float(interval) / 1000)
    sampler.start()

    dumper = Dumper(sample_queue, recording_file)
    dumper.start()

    start = time()
    end = duration and start + duration

    try:
        echo('Sampling Mongo...')

        left = end - time()
        while not duration or left > 0:
            sleep(duration and min(left, 3) or 3)
            echo('  %6d samples  %6d ops' % (
                sampler.num_samples, sampler.num_ops))
            left = end - time()
    except KeyboardInterrupt:
        echo()
        echo(style('Stopping', fg='red'))
    else:
        if sampler.num_dropped:
            echo('%s dropped %d / %d (%.2f%%) samples - unable to keep up' % (
                style('WARNING:', fg='red'),
                sampler.num_dropped,
                sampler.num_samples,
                100.0 * sampler.num_dropped / sampler.num_samples))

        echo('Finalizing recording of samples')

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
def analyze(recording_file, focus=None, num_top=None):
    reporter = Reporter(list(decode_file_iter(recording_file)))

    echo('== Stats ==')
    for stat, val in sorted(reporter.get_stats().items()):
        echo('  %s = %s' % (stat, val))
    echo()

    groupings = reporter.get_groupings()

    # Optionally focus on one grouping
    if focus:
        groupings = {focus: groupings[focus]}
    elif num_top is None:
        # If not explicitly told to show all, default to 5
        num_top = 5

    reporter.print_top(groupings, num_top=num_top)
