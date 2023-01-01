import importlib
import json
import os
import traceback
import typing

import modular
import modules.logging
import modules.eval
import modules.repeat
import modules.mapper
import modules.ping

importlib.reload(modular)
importlib.reload(modules.logging)
importlib.reload(modules.eval)
importlib.reload(modules.repeat)
importlib.reload(modules.mapper)

ALIASES = {
    # 'sc': 'score'
}

TRIGGERS = {
    # r'^You are thirsty\.$': 'drink waterskin'
}

if os.path.exists("passwords_mongoose.json"):
    with open("passwords_mongoose.json", "rb") as pws:
        TRIGGERS.update(json.load(pws))


class Mongoose(modular.ModularClient):
    def __init__(self, mud, name):

        self.name = name
        self.logfname = "mongoose.log"
        self.mapfname = "mongoose.map"

        self.modules = {}
        mods = {
            "eval": (modules.eval.Eval, []),
            # "repeat": (modules.repeat.Repeat, []),
            "logging": (modules.logging.Logging, [self.logfname]),
            "mapper": (modules.mapper.Mapper, [True, self.mapfname, True]),
            "ping": (modules.ping.Ping, [])
        }

        for modname, module in mods.items():
            try:
                constructor, args = module
                args = [mud] + args
                self.modules[modname] = constructor(*args)
            except Exception:
                traceback.print_exc()

        super().__init__(mud)

        self.aliases.update(ALIASES)
        self.triggers.update(TRIGGERS)

    def getHostPort(self) -> tuple[str, int]:
        return "mongoose.moo.mud.org", 7777


def getClass() -> typing.Any:
    return Mongoose
