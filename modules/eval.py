from pprint import pformat
from typing import Any

from modules.basemodule import BaseModule


class Eval(BaseModule):
    locals: dict[str, Any] = {}

    def alias(self, line: str) -> bool:
        if line.startswith('#py '):
            rest = line[4:]
            self.mud.log("\n" + pformat(eval(rest, self.globals(), self.locals)))
            return True
        elif line.startswith('#pye '):
            rest = line[5:]
            exec(rest, self.globals(), self.locals)
            return True
        return False

    def globals(self) -> dict[str, Any]:
        return {
            'self': self,
            'mud': self.mud,
            'session': self.mud,
            'world': self.mud.world,
            'gmcp': self.mud.world.gmcp,
            'state': self.mud.world.state,
            'modules': self.mud.world.modules,
        }
