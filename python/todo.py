import sys

import parser
from main_loop import main_loop
from script_utils import parse_args
import os_utils
from settings import get_todo_file

SETTINGS = '~/.config/vim-todo/config.txt'
PID = '~/.config/vim-todo/.pid'

if __name__ != "__main__":
    import os_utils.die

    os_utils.die("This should be run as a standalone app")

args = parse_args()

if args.restart:
    os_utils.stop_daemon(PID)
    todo_file = get_todo_file(args, SETTINGS)
    os_utils.start_daemon(PID)
    main_loop(todo_file, args.dry_run)
elif args.stop:
    os_utils.stop_daemon(PID)
elif args.no_daemon:
    todo_file = get_todo_file(args, SETTINGS)
    main_loop(todo_file, args.dry_run)
elif args.verify:
    todo_file = get_todo_file(args, SETTINGS)
    error = False

    lineno = 0
    for td in parser.process_todo_file(todo_file):
        lineno += 1
        if td.error is not None:
            error = True
            sys.stderr.write(
                "%s:%d in line %s ERROR %s" % (todo_file, lineno, td.text, td.error))

    if error:
        exit(1)
else:
    todo_file = get_todo_file(args, SETTINGS)
    os_utils.start_daemon(PID)
    main_loop(todo_file, args.dry_run)
