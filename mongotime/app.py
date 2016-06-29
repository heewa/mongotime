from __future__ import absolute_import

from time import sleep
from Queue import Queue

import click
from click import echo, style

from pymongo import MongoClient

from .sampler import Sampler
from .dumper import Dumper
from .reporter import Reporter
from .samples import DumpedSamples, ServedSamples


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
@click.option('--duration', '-d', default=3, help='Duration in sec to sample')
@click.argument('dumpfile', type=click.File('wb'))
@click.pass_context
def dump(ctx, dumpfile, interval, duration):
    sample_queue = Queue(maxsize=100)

    sampler = Sampler(
        ctx.obj['db'],
        sample_queue,
        interval_sec=float(interval) / 1000)
    sampler.start()

    dumper = Dumper(sample_queue, dumpfile)
    dumper.start()

    try:
        echo('Sampling Mongo...')
        sleep(duration)
    except KeyboardInterrupt:
        echo()
        echo(style('Stopping', fg='red'))
    else:
        echo('Finalizing dump')

    sampler.stop()
    dumper.stop()


@cli.command()
def serve():
    echo('Serving a profile')


@cli.group()
def report():
    pass


@report.command('dump')
@click.argument('dumpfile', type=click.File('rb'))
@click.option('--short/--long', default=True)
@click.option('--query')
def report_dump(dumpfile, **kwargs):
    run_report(DumpedSamples(dumpfile), **kwargs)


@report.command('server')
@click.argument('server', default='localhost:%d' % DEFAULT_PORT)
@click.option('--short/--long', default=True)
@click.option('--query')
def report_server(server, **kwargs):
    if ':' in server:
        host, port = server.rsplit(':', 1)
        port = int(port)
    else:
        host, port = server, DEFAULT_PORT
    run_report(ServedSamples(host, port), **kwargs)


def run_report(samples, short=None, query=None):
    reporter = Reporter(samples, query=query)
    reporter.stats()
    echo()
    reporter.top()
