from typing import Any

import lark

with open('moo.lark') as f:
    lex = lark.Lark(f.read())


class MooList(list):
    def __repr__(self) -> str:
        s = '{'
        first = True
        for i in self:
            if not first:
                s += ', '
            s += repr(i)
            first = False
        s += '}'
        return s

class MooObj(str):
    def __repr__(self) -> str:
        return super().__str__()

class MooStr(str):
    def __repr__(self) -> str:
        return super().__str__()



class MooToPy(lark.Transformer):
    list = MooList
    ESCAPED_STRING = MooStr
    OBJ_NUM = MooObj
    SIGNED_INT = int

    def start(self, s):
        return s[0]

def parse_value(string: str) -> Any:
    tree = lex.parse(string)
    return MooToPy().transform(tree)
