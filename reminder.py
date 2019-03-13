from os.path import expanduser
from os.path import isfile
import sys
import os
import datetime
import signal
from typing import Callable, Sequence, Optional
from dataclasses import dataclass

SETTINGS = expanduser('~/.reminderrc')
PID = expanduser('~/.reminderpid')


def die(exit_code, message):
    sys.stderr.write(message)
    exit(exit_code)


def stop_daemon(pid_file):
    import select
    if not isfile(PID):
        die(1, 'There is no daemon process started')
    else:
        fd = None
        kq = None
        try:
            fd = open(pid_file, 'r')
            pid = int(fd.read())
            kq = select.kqueue()
            ke = select.kevent(pid,
                               filter=select.KQ_FILTER_PROC,
                               flags=select.KQ_EV_ADD | select.KQ_EV_CLEAR,
                               fflags=select.KQ_NOTE_EXIT)
            os.kill(pid, signal.SIGUSR1)
            for _ in kq.control([ke], 1, 5):
                pass
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        finally:
            if kq is not None:
                kq.close()
            if fd is not None:
                fd.close()


def start_daemon(pid_file, stdin_file=None, stdout_file=None, stderr_file=None):
    if isfile(pid_file):
        die(2, 'Reminder daemon is already started. To restart, call with --restart argument')
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # decouple from parent environment
    # os.chdir("/")
    os.setsid()
    os.umask(0)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    if stdin_file is None:
        si = open(os.devnull, 'r')
    else:
        si = open(stdin_file, 'r')
    os.dup2(si.fileno(), sys.stdin.fileno())
    if stdout_file is None:
        so = open(os.devnull, 'w')
    else:
        so = open(stdout_file, 'a+')
    os.dup2(so.fileno(), sys.stdout.fileno())
    if stderr_file is None:
        se = open(os.devnull, 'w')
    else:
        se = open(stderr_file, 'a+', 0)
    os.dup2(se.fileno(), sys.stderr.fileno())

    # write pidfile
    import atexit
    atexit.register(lambda: os.remove(pid_file))
    import signal
    signal.signal(signal.SIGUSR1, lambda: exit())
    pid = str(os.getpid())
    fd = open(pid_file, 'w+')
    try:
        fd.write("%s\n" % pid)
    finally:
        fd.close()


def parse_args():
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

    return arguments.parse_args()


def create_block_parser():
    from lark import Lark
    parser = Lark('''
    reminder : "remind" "me" instruction
             | "^" NUMBER ":" reminder         -> reminder_with_data
    
    instruction: "in" time_spans               -> instruction_in
               | "on" date  time_correction?   -> instruction_on
               | "tomorrow" time_correction?   -> ins_tom
               
    time_spans: [ time_span +] -> time_spans
    
    time_span: NUMBER time_spec
             
    time_spec: "m"          -> minutes 
             | "minute"     -> minutes
             | "minutes"    -> minutes
             | "h"          -> hours
             | "hr"         -> hours
             | "hrs"        -> hours
             | "hour"       -> hours
             | "hours"      -> hours
             | "s"          -> seconds
             | "seconds"    -> seconds
             
    date: "Monday"          -> mon
        | "Tuesday"         -> tue
        | "Wednesday"       -> wed
        | "Thursday"        -> thu
        | "Friday"          -> fri
        | "Saturday"        -> sat
        | "Sunday"          -> sun
        
    time_correction: "morning"         -> morning
                   | "evening"         -> evening
                   | "lunch"           -> lunch
                   | "noon"            -> noon
    
    %import common.WS
    %import common.NUMBER
    %ignore WS
    ''', start='reminder')
    return parser


def process_reminder_ast(tree):
    from lark import Transformer
    import datetime

    def next_weekday(d: datetime, weekday: int):
        days_ahead = weekday - d.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return d + datetime.timedelta(days_ahead)

    class TreeToDate(Transformer):
        def reminder_with_data(self, r):
            return datetime.datetime.fromtimestamp(int(r[0].value))

        def reminder(self, r):
            return r[0]

        def time_span(self, span):
            return int(span[0].value) * span[1]

        def minutes(self, m):
            return 60

        def hours(self, h):
            return 60 * 60

        def seconds(self, s):
            return 1

        def instruction_in(self, instructions):
            res = sum(instructions)
            return (datetime.datetime.today() + datetime.timedelta(seconds=res))

        def time_spans(self, spans):
            return sum(spans)

        def instruction_on(self, date_lambda):
            res = datetime.datetime.today()
            for l in date_lambda:
                res = l(res)
            return res

        def ins_tom(self, date_lambda):
            res = datetime.datetime.today() + datetime.timedelta(days=1)
            for l in date_lambda:
                res = l(res)
            return res

        def mon(self, _):
            return lambda d: next_weekday(d, 0)

        def tue(self, _):
            return lambda d: next_weekday(d, 1)

        def wed(self, _):
            return lambda d: next_weekday(d, 2)

        def thu(self, _):
            return lambda d: next_weekday(d, 3)

        def fri(self, _):
            return lambda d: next_weekday(d, 4)

        def sat(self, _):
            return lambda d: next_weekday(d, 5)

        def sun(self, _):
            return lambda d: next_weekday(d, 6)

        def morning(self, _):
            return lambda d: d.replace(hour=9, minute=0)

        def evening(self, _):
            return lambda d: d.replace(hour=16, minute=0)

        def lunch(self, _):
            return lambda d: d.replace(hour=12, minute=0)

        def noon(self, _):
            return lambda d: d.replace(hour=13, minute=0)

    return TreeToDate().transform(tree)


def test_process_reminder_ast():
    from datetime import datetime
    from datetime import timedelta

    def tomorrow():
        return datetime.today() + timedelta(days=1)

    parser = create_block_parser()

    def parse_and_process(text) -> datetime:
        return process_reminder_ast(parser.parse(text))

    assert parse_and_process("remind me tomorrow") - tomorrow() <= timedelta(seconds=1)

    tom_eve = parse_and_process("remind me tomorrow evening")
    assert tom_eve.day - tomorrow().day == 0
    assert tom_eve.hour == 16
    assert tom_eve.minute == 0

    tom_morn = parse_and_process("remind me tomorrow morning")
    assert tom_morn.day - tomorrow().day == 0
    assert tom_morn.hour == 9
    assert tom_morn.minute == 0

    in_2_hrs = parse_and_process("remind me in 2hrs 10 minutes")
    assert in_2_hrs.hour - datetime.today().hour == 2
    assert in_2_hrs.minute - datetime.today().minute == 10

    fri = parse_and_process("remind me on Tuesday evening")
    assert fri.weekday() == 1
    assert fri.hour == 16

    with_data = parse_and_process("^15:remind me in 2 hours")
    assert with_data.timestamp() == 15


@dataclass
class TodoEntry:
    text: str
    new_reminder: bool
    reminder: Optional[datetime.datetime] = None
    error: Optional[str] = None


def process_todo_file(settings_file: str) -> Sequence[TodoEntry]:
    end_of_tasks = '-' * 50
    block_parser = None
    fd = None
    try:
        fd = open(settings_file)
        in_reminder_section = True
        lineno = 0
        for line in fd:
            lineno += 1
            if line.startswith(end_of_tasks):
                in_reminder_section = False
            if in_reminder_section:
                if line.lstrip().startswith('*'):
                    block_start = line.find('[')
                    if block_start == -1:
                        yield TodoEntry(line, False, None, None)
                        continue
                    block_end = line.find(']', block_start)
                    block = line[block_start + 1: block_end]
                    if block.startswith("!"): # event from the past
                        yield TodoEntry(line, False, None, None)
                        continue
                    if block_parser is None:
                        block_parser = create_block_parser()
                    try:
                        res = block_parser.parse(block)
                        res = process_reminder_ast(res)
                        yield TodoEntry(line, not block.startswith('^'), res, None)
                    except Exception as e:
                        yield TodoEntry(line, True, None, str(e).replace('line 1', 'line '+str(lineno)))
                else:
                    yield TodoEntry(line, False, None, None)
            else:
                yield TodoEntry(line, False, None, None)
        pass
    finally:
        if fd is not None: fd.close()


def wait_for_file_update(file, callback: Callable) -> None:
    import select

    def monitor_file() -> bool:  # True if should restart monitoring
        fd = None
        kq = None
        try:
            fd = open(file)
            callback()
            kq = select.kqueue()
            kevent = select.kevent(fd.fileno(),
                                   filter=select.KQ_FILTER_VNODE,
                                   flags=select.KQ_EV_ADD | select.KQ_EV_CLEAR,
                                   fflags=select.KQ_NOTE_WRITE | select.KQ_NOTE_RENAME | select.KQ_NOTE_DELETE)
            renamed = False
            while True:
                revents = kq.control([kevent], 1, None)
                for evt in revents:
                    if evt.flags & select.KQ_EV_ERROR == select.KQ_EV_ERROR:
                        raise select.error(evt.data)
                    if evt.fflags & select.KQ_NOTE_WRITE:
                        callback()
                    if evt.fflags & select.KQ_NOTE_RENAME:
                        renamed = True
                    if evt.fflags & select.KQ_NOTE_DELETE:
                        return renamed
        finally:
            if kq is not None: kq.close()
            if fd is not None: fd.close()

    while monitor_file():
        pass


def copy_file(file_from, file_to):
    fd_from = None
    fd_to = None
    try:
        fd_from = open(file_from)
        fd_to = open(file_to, "w")
        for line in fd_from:
            fd_to.write(line)
    finally:
        if fd_to is not None:
            fd_to.close()
        if fd_from is not None:
            fd_from.close()

@dataclass
class Reminder:
    when: datetime
    text: str
    def seconds_from_now(self):
        return int(self.when.timestamp() - datetime.datetime.now().timestamp())


def show_notification(title, subtitle):
    os.system("osascript -e 'display notification \"%s\" with title \"%s\"' " % (subtitle, title))


def nice_reminder_text(text: str) -> str:
    res = ""
    skip = 0
    for c in text:
        if c == '[':
            skip += 1
        elif c == ']':
            skip -= 1
            if skip < 0:
                skip = 0
        elif skip == 0:
            res += c
    return res


def mark_reminder_as_completed(settings_file: str, reminder: Reminder):
    fd = open(settings_file)
    lines = []
    for line in fd:
        if line == reminder.text:
            line = line.replace('[^', '[!')
        lines.append(line)
    fd.close()
    fd = open(settings_file, "w")
    fd.writelines(lines)
    fd.close()


def show_reminders(settings_file, reminders):
    while True:
        first = min(reminders, key=lambda r: r.when)
        if first.seconds_from_now() <= 0:
            print("showing reminder for", first.text.rstrip())
            mark_reminder_as_completed(settings_file, first)
            show_notification("Todo reminder from %s" % settings_file, nice_reminder_text(first.text.rstrip()))
            reminders.remove(first)
            return # by changing file, we caused us to read it again and at the end we will end up in this function
        else:
            break

    print("next reminder at", first.when, "in", first.seconds_from_now(), "is", first.text.rstrip())

    signal.signal(signal.SIGALRM, lambda sig, frm: show_reminders(settings_file, reminders))
    if first is not None:
        signal.alarm(first.seconds_from_now())


def main_loop(settings_file):
    def process():
        import tempfile

        tmp_fd, tmp_file_name = tempfile.mkstemp("todo")
        out = open(tmp_fd, "w")
        has_changes = False
        lineno = 0
        reminders = []
        for td in process_todo_file(settings_file):
            lineno += 1
            line = td.text
            if td.reminder is not None:
                if td.new_reminder:
                    line = td.text.replace("remind me",
                                           "^" + str(int(td.reminder.timestamp())) + ":remind me")
                    has_changes = True
                reminders.append(Reminder(td.reminder, td.text))
            if td.error is not None:
                sys.stderr.write(
                    "%s:%d in line %s ERROR %s" % (todo_file, lineno, td.text, td.error))
            out.write(line)
        out.close()
        if has_changes:
            print("updated", settings_file)
            # calling replace plays bad game with our monitoring: loosing ability to monitor file
            # os.replace(tmp_file_name, settings_file)
            copy_file(tmp_file_name, settings_file)
            os.remove(tmp_file_name)
        else:
            os.remove(tmp_file_name)
        show_reminders(settings_file, reminders)


    wait_for_file_update(settings_file, process)


def get_todo_file(args, settings):
    if args.todo_file is not None:
        todo_file = args.todo_file
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


if __name__ == '__main__':
    args = parse_args()
    if args.restart:
        stop_daemon(PID)
        todo_file = get_todo_file(args, SETTINGS)
        start_daemon(PID)
        main_loop(todo_file)
    elif args.stop:
        stop_daemon(PID)
    elif args.no_daemon:
        todo_file = get_todo_file(args, SETTINGS)
        main_loop(todo_file)
    elif args.verify:
        todo_file = get_todo_file(args, SETTINGS)
        error = False

        lineno = 0
        for td in process_todo_file(todo_file):
            lineno += 1
            if td.error is not None:
                error = True
                sys.stderr.write(
                    "%s:%d in line %s ERROR %s" % (todo_file, lineno, td.text, td.error))

        if error:
            exit(1)
    else:
        todo_file = get_todo_file(args, SETTINGS)
        start_daemon(PID)
        main_loop(todo_file)
