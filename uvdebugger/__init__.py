import re
import atexit
import click
from pathlib import Path
from code import interact
from transaction import TransactionManager


def should_commit(txn):
    def commiter():
        if txn.isDoomed():
            print('Abort.')
            txn.abort()
        else:
            print('Commit.')
            txn.commit()
    return commiter


class InteractionRequest:

    def __init__(self, app, t):
        self.app = app
        self.transaction = t

    def get_crud(self, ct):
        content_type = self.app.contents[ct]
        factory = app.database.create_utility(
            transaction_manager=self.transaction
        )
        crud = factory(content_type.model)
        return content_type, crud


def python_shell_runner(env, help, interact=interact):
    cprt = 'Type "help" for more information.'
    banner = f"Python {sys.version} on {sys.platform}\n{cprt}"
    banner += '\n\n' + help + '\n'

    import readline
    import rlcompleter
    import code
    import os
    from glob import glob

    history_path = os.path.expanduser("~/.python_history")

    def save_history(history_path=history_path):
        readline.write_history_file(history_path)
    if os.path.exists(history_path):
        readline.read_history_file(history_path)

    atexit.register(save_history)

    readline.set_completer(rlcompleter.Completer(env).complete)
    readline.parse_and_bind("tab: complete")
    code.InteractiveConsole(locals=env).interact(banner)


h = """
WELCOME TO UV-X Debugger
you can use the global request
"""


RUNNER_PATTERN = re.compile(
    r"""
    ^
    (?P<module>
        [a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*
    )
    :
    (?P<object>
        [a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*
    )
    $
    """,
    re.I | re.X,
)


def resolve(name):
    """Resolve a named object in a module.
    """
    def match(name):
        matches = RUNNER_PATTERN.match(name)
        if not matches:
            raise ValueError(f"Malformed application '{obj_name}'")
        return matches.group("module"), matches.group("object")

    module_name, object_name = match(name)
    segments = [str(segment) for segment in object_name.split(".")]
    obj = __import__(module_name, fromlist=segments[:1])
    for segment in segments:
        obj = getattr(obj, segment)
    return obj


@click.command()
@click.argument("app")
@click.option("--script", default=None, help="Script to run in context.")
def debugger(app: str, script: str = None):
    obj = resolve(app)
    manager = TransactionManager()
    txn = manager.begin()
    env = {
        'request': InteractionRequest(obj, manager),
        'transaction': txn
    }
    atexit.register(should_commit(txn))
    if script is None:
        python_shell_runner(env, h)
    else:
        path = Path(script)
        if not path.exists() or not path.is_file():
            raise RuntimeError(f'Script needs to be a python file.')
        with path.open('r') as fd:
            code = fd.read()
        exec(code, env)
