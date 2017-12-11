from __future__ import absolute_import

from time import sleep, time
from Queue import Queue

import click
from click import echo, style

from pymongo import MongoClient

from .sampler import Sampler
from .dumper import Dumper
from .reporter import Reporter
from .samples import DumpedSamples


DEFAULT_PORT = 2846


def run():
    cli(obj={})


@click.group()
@click.option('--db', default='localhost:27017', help='Location of Mongo host')
@click.pass_context
def cli(ctx, db):
    ctx.obj['db'] = MongoClient(db)


@cli.command()
@click.option('--interval', '-i', default=100, help='Sampling interval in ms')
@click.option('--duration', '-d', default=0, help='Duration in sec to record')
@click.argument('recording_file', type=click.File('wb'))
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
        echo('Finalizing recording of samples')

    sampler.stop()
    dumper.stop()


@cli.command()
@click.argument('recording_file', type=click.File('rb'))
def report(recording_file, **kwargs):
    run_report(DumpedSamples(recording_file), **kwargs)


def run_report(samples, query=None):
    reporter = Reporter(samples, query=query)
    reporter.stats()
    echo()
    reporter.top()
