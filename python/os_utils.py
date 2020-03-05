import os
import signal
import sys
from collections import Callable


def die(exit_code, message):
    sys.stderr.write(message)
    exit(exit_code)


def stop_daemon(pid_file):
    import select
    if not os.path.isfile(pid_file):
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
    if os.path.isfile(pid_file):
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


def show_notification(title, subtitle):
    os.system("osascript -e 'display notification \"%s\" with title \"%s\"' " % (subtitle, title))


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
