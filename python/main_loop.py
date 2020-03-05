import os
import signal
import sys

from os_utils import copy_file, show_notification, wait_for_file_update
from parser import process_todo_file, Reminder


def mark_reminder_as_completed(todo_file: str, reminder: Reminder, dry_run: bool):
    fd = open(todo_file)
    lines = []
    for line in fd:
        if line == reminder.text:
            line = line.replace('[^', '[!')
            if dry_run:
                print("dry_run: updating reminder line: ", line)
        lines.append(line)
    fd.close()
    if not dry_run:
        fd = open(todo_file, "w")
        fd.writelines(lines)
        fd.close()


def show_reminders(todo_file, reminders, dry_run: bool):
    while True:
        first = min(reminders, key=lambda r: r.when)
        if first.seconds_from_now() <= 0:
            print("showing reminder for", first.text.rstrip())
            mark_reminder_as_completed(todo_file, first, dry_run)
            if not dry_run:
                show_notification("Todo reminder from %s" % todo_file, nice_reminder_text(first.text.rstrip()))
            reminders.remove(first)
            return  # by changing file, we caused us to read it again and at the end we will end up in this function
        else:
            break

    print("next reminder at", first.when, "in", first.seconds_from_now(), "is", first.text.rstrip())

    signal.signal(signal.SIGALRM, lambda sig, frm: show_reminders(todo_file, reminders, dry_run))
    if first is not None:
        signal.alarm(first.seconds_from_now())


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


def main_loop(todo_file, dry_run: bool):
    def process():
        import tempfile

        tmp_fd, tmp_file_name = tempfile.mkstemp("todo")
        out = open(tmp_fd, "w")
        has_changes = False
        lineno = 0
        reminders = []
        for td in process_todo_file(todo_file):
            lineno += 1
            line = td.text
            if td.reminder is not None:
                if td.new_reminder:
                    line = td.text.replace("remind me",
                                           "^" + str(int(td.reminder.timestamp())) + ":remind me")
                    if dry_run:
                        print("dry_run: "+line)
                    has_changes = True
                reminders.append(Reminder(td.reminder, td.text))
            if td.error is not None:
                sys.stderr.write(
                    "%s:%d in line %s ERROR %s" % (todo_file, lineno, td.text, td.error))
            out.write(line)
        out.close()
        if has_changes:
            if dry_run:
                print("dry_run: in normal mode would update", todo_file)
            else:
                print("updated", todo_file)
                # calling replace plays bad game with our monitoring: loosing ability to monitor file
                # os.replace(tmp_file_name, settings_file)
                copy_file(tmp_file_name, todo_file)
        os.remove(tmp_file_name)
        show_reminders(todo_file, reminders, dry_run)

    wait_for_file_update(todo_file, process)
