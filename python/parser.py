import datetime
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass
class Reminder:
    when: datetime
    text: str

    def seconds_from_now(self):
        return int(self.when.timestamp() - datetime.datetime.now().timestamp())

@dataclass
class TodoEntry:
    text: str
    new_reminder: bool
    reminder: Optional[datetime.datetime] = None
    error: Optional[str] = None


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
             | "day"        -> days
             | "days"       -> days
             | "d"          -> days
             
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

        def days(self, d):
            return self.hours(24)

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
                    if block.startswith("!"):  # event from the past
                        yield TodoEntry(line, False, None, None)
                        continue
                    if block_parser is None:
                        block_parser = create_block_parser()
                    try:
                        res = block_parser.parse(block)
                        res = process_reminder_ast(res)
                        yield TodoEntry(line, not block.startswith('^'), res, None)
                    except Exception as e:
                        yield TodoEntry(line, True, None, str(e).replace('line 1', 'line ' + str(lineno)))
                else:
                    yield TodoEntry(line, False, None, None)
            else:
                yield TodoEntry(line, False, None, None)
        pass
    finally:
        if fd is not None: fd.close()
