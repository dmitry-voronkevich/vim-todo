from os.path import isfile, expanduser
from os_utils import die
from script_utils import Arguments


def get_todo_file(args: Arguments, settings):
    if args.file is not None:
        todo_file = args.file
    else:
        if not isfile(settings):
            die(3, 'there is no %s, which I use for settings' % settings)
        fd = open(settings, 'r')
        try:
            todo_file = fd.readline()
            todo_file = todo_file.rstrip()
            todo_file = expanduser(todo_file)
        finally:
            fd.close()
    if not isfile(todo_file):
        die(4, "can't find todo file %s" % (todo_file))
    return todo_file
