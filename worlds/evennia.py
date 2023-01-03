import importlib
import traceback

import modular
import modules.eval
import modules.logging
import modules.mapper
import modules.repeat

importlib.reload(modular)
importlib.reload(modules.logging)
importlib.reload(modules.eval)
importlib.reload(modules.repeat)
importlib.reload(modules.mapper)

ALIASES={}

TRIGGERS={}

class Evennia(modular.ModularClient):
    def __init__(self, mud, name):

        self.name = name
        self.logfname = '{}.log'.format(name)
        self.mapfname = 'evennia.map'.format(name)

        self.modules = {}
        mods = {
                'eval': (modules.eval.Eval, []),
                'repeat': (modules.repeat.Repeat, []),
                'logging': (modules.logging.Logging, [self.logfname]),
                'mapper': (modules.mapper.Mapper, [True, self.mapfname, True]),
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

    def getHostPort(self):
        return 'localhost', 4000

def getClass():
    return Evennia
