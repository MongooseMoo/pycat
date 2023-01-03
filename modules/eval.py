from pprint import pformat
from typing import Any

from modules.basemodule import BaseModule


class Eval(BaseModule):
    def alias(self, line):
        if line.startswith('#py '):
            rest = line[4:]
            self.mud.log("\n" + pformat(eval(rest, self.globals())))
            return True
        elif line.startswith('#pye '):
            rest = line[5:]
            exec(rest)
            return True

    def globals(self) -> dict[str, Any]:
        return {
            'self': self,
            'mud': self.mud,
            'world': self.mud.world,
            'gmcp': self.mud.world.gmcp,
            'state': self.mud.world.state,
            'modules': self.mud.world.modules,
        }
