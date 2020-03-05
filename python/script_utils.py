from dataclasses import dataclass


@dataclass
class Arguments:
    restart: bool
    stop: bool
    no_daemon: bool
    verify: bool
    dry_run: bool
    file: str


def parse_args() -> Arguments:
    import argparse
    arguments = argparse.ArgumentParser("Monitors your todo.txt file for reminders")
    arguments.add_argument('--restart', help="restarts daemon which monitors todo file",
                           action='store_true')
    arguments.add_argument('--stop', help='stops daemon which monitors todo file',
                           action='store_true')
    arguments.add_argument('--file', dest='todo_file')
    arguments.add_argument('--no-daemon', dest='no_daemon', action='store_true',
                           help='run as a regular process, do not create daemon')
    arguments.add_argument('--verify', help="verify your todo file and then exists",
                           action='store_true')
    arguments.add_argument("--dry-run", help="run in the debug mode, report all information and exit",
                           action="store_true")

    args = arguments.parse_args()
    return Arguments(
        restart=args.restart,
        stop=args.stop,
        no_daemon=args.no_daemon,
        verify=args.verify,
        dry_run=args.dry_run,
        file=args.todo_file,
    )
