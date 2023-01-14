#!/usr/bin/env python3

import importlib
import os

import click
from session import Session

if not os.path.exists('data'):
    os.mkdir('data')
os.chdir('data')

@click.command()
@click.option("--bind", default=os.environ.get('PYCAT_BIND', 'localhost'), help='Bind Address', show_default=True)
@click.option('--terminate-on-disconnect', is_flag=True, help='Quit pycat when the MUD disconnects')
@click.argument("world", default=lambda: os.environ.get('PYCAT_WORLD'))
@click.argument("port", default=lambda: os.environ.get('PYCAT_PORT', 7777))
@click.argument('arg', default=lambda: os.environ.get('PYCAT_ARG', ""))
def main(world: str, port: str | int, arg: str, bind: str, terminate_on_disconnect: bool, **kwargs: str) -> None:
    if world:
        world_module = importlib.import_module('worlds.' + world)
    else:
        world_module = importlib.import_module('portal')
    port = int(port)
    ses = Session(world_module, port, arg, bind, terminate_on_disconnect)
    ses.run()


if __name__ == '__main__':
    main.main()
