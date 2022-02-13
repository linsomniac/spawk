#!/usr/bin/env python3

import sys
import click
from functools import update_wrapper

@click.group(chain=True)
def cli():
    '''The main help
    '''

@cli.result_callback()
def process_commands(processors):
    '''This result callback is involked with an iterable of all the chained subcommands.
    As in this example eace subcommand returns a function we can chain them together to feed
    one into the other, similar to how a pipe on unix works.
    '''
    stream = ()

    for processor in processors:
        stream = processor(stream)

    if stream is not None:
        for _ in stream:
            sys.stdout.write(_)

def processor(f):
    '''Helper decorator to rewrite a function so that it returns another function from it.'''
    def new_func(*args, **kwargs):
        def processor(stream):
            return f(stream, *args, **kwargs)
        return processor
    return update_wrapper(new_func, f)

def generator(f):
    '''Similar to the :func:`processor` but passes through old values unchanged and does not
    pass through the values as parameter'''

    @processor
    def new_func(stream, *args, **kwargs):
        yield from stream
        yield from f(*args, **kwargs)
    return update_wrapper(new_func, f)

@cli.command('input')
@click.argument('filename')
@click.option(
    '-s', '--state-file',
    type=click.Path(),
    help='File to store and load input file state'
)
@click.option(
    '-F', '--follow/--no-follow', default=False,
    help='When at EOF, wait for more data to be appended and if file is re-created start '
        'reading the new file'

)
@generator
def input_cmd(filename, state_file, follow):
    with open(filename, 'r') as fp:
        for line in fp:
            yield line


@cli.command('upper')
@processor
def upper_cmd(stream):
    for x in stream:
        yield x.upper()


@cli.command('output')
@processor
def output_cmd(stream):
    for x in stream:
        sys.stdout.write(x)


@cli.command('tee')
@click.argument('filename')
@processor
def tee_cmd(stream, filename):
    with open(filename, 'w') as fp:
        for x in stream:
            fp.write(x)
            yield(x)
