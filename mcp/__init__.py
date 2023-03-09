from typing import Sequence
from .basepackage import PACKAGES, McpPackage
from .mcp_negotiate import Negotiate
from .vmoo_userlist import VMooUserlist

__all__ = ["PACKAGES", "McpPackage", "Negotiate", "VMooUserlist", "parse_mcp_vars"]


def parse_mcp_vars(parts: Sequence[str | bytes]) -> dict[str, str]:
    vars: dict[str, str] = {}
    k = ''
    v = ''
    for p in parts[2:]:
        if isinstance(p, bytes):
            p = p.decode()
        if p.endswith(':'):
            if k:
                if v.startswith('""') and v.endswith('""'):
                    v = v.strip('"')
                vars[k] = v
            k = p[:-1]
            v = ''
        else:
            if v.startswith('"'):
                v += f' {p}'
            else:
                v = p
    vars[k] = v
    return vars
