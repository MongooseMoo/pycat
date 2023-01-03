from typing import Any


class BaseModule(object):
    def __init__(self, mud) -> None:
        self.mud = mud

    def send(self, line):
        return self.mud.send(line)

    def show(self, line):
        return self.mud.show(line)

    def log(self, *args, **kwargs):
        return self.mud.log(*args, **kwargs)

    def getTriggers(self):
        return {}

    def getAliases(self):
        return {}

    # Timers are names mapped to tuples of (oneshot, period, remaining time until period boundary, callable)
    def getTimers(self):
        return {}

    def mktimer(self, period: int, fn: callable, oneshot: bool = False) -> dict[str, Any]:
        return self.world.mktimer(period, fn, oneshot)

    def mkdelay(self, *args):
        return self.world.mkdelay(*args)

    def quit(self):
        pass
