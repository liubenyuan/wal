'''Implementation of basic read-eval-print-loop'''
# pylint: disable=W0703,C0103
import cmd
import readline
import os

from wal.util import wal_str
from wal.reader import read_wal_sexpr, ParseError
from wal.passes import expand, optimize, resolve
from wal.ast_defs import Operator, Symbol
from wal.trace.trace import Trace
from wal.version import __version__

histfile = os.path.expanduser('~/.wal/.wal_history')
histfile_size = 1000

class WalRepl(cmd.Cmd):
    '''WalRepl class implements basic read-eval-print-loop'''


    std_intro = f'''WAL {__version__}
Exit to OS or terminate running evaluations with CTRL-C'''
    dyn_intro = f'''WAL {__version__}
Started interactive WAL REPL.
Exit to calling script or terminate running evaluations with CTRL-C'''

    terminator = ['(', ')']
    complete_list = [op.value for op in Operator]
    file = None

    def __init__(self, wal, intro=std_intro):
        super().__init__()
        self.wal = wal
        self.intro = intro

    @property
    def prompt(self):
        '''Generate prompt symbol'''
        traces = ', '.join(self.wal.traces.traces.keys())
        if self.wal.traces.traces:
            traces = traces + ' '
        return f'{traces}>-> '


    def onecmd(self, line):
        try:
            expanded = expand(self.wal.eval_context, line, parent=self.wal.eval_context.global_environment)
            optimized = optimize(expanded)
            resolved = resolve(optimized, start=self.wal.eval_context.global_environment.environment)
            evaluated = self.wal.eval(resolved)

            if evaluated is not None:
                print(wal_str(evaluated))

            if readline: # pylint: disable=W0125
                readline.set_history_length(histfile_size)
                readline.write_history_file(histfile)

        except KeyboardInterrupt:
            print('Keyboard Interrupt')
        except Exception as e:
            print(e)
            print(wal_str(line))


    def precmd(self, line):
        try:
            sexpr = read_wal_sexpr(line)
            # intercept defuns to include them in completion
            if isinstance(sexpr, list):
                if sexpr[0] == Symbol('defun'):
                    self.complete_list.append(sexpr[1].name)

            return sexpr
        except ParseError as e:
            e.show()
        except Exception as e:  # pylint: disable=W0703,C0103
            print(e)
        return None

    def complete(self, text, state):
        return self.completenames(text)[state]

    def completenames(self, text, *ignored):
        tmp = self.complete_list + self.wal.traces.signals

        if len(self.wal.traces.traces) == 1:
            tmp += Trace.SPECIAL_SIGNALS

        candidates = [c for c in tmp if c.startswith(text)]
        candidates.append(None)
        return candidates

    def preloop(self):
        if not os.path.exists(histfile):
            os.makedirs(os.path.expanduser('~/.wal'), exist_ok=True)

        if readline and os.path.exists(histfile):
            readline.read_history_file(histfile)
