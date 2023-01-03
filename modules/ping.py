import telnetlib
from typing import Any

from modules.basemodule import BaseModule


class Ping(BaseModule):
    """
    Periodically sends an AYT (Are you there) package, to ensure NAT'd connections aren't closed for being silent too long.

    We use an AYT so that the mud doesn't update the idle time of the player.
    """
    def getTimers(self) -> dict[str, Any]:
        return {
            "ping": self.mktimer(60, self.ping, False),
        }

    def ping(self, mud) -> None:
        mud.mud.telnet.sock.sendall(telnetlib.AYT)
        # mud.mud.pipeToSocketW.write(telnetlib.AYT)
        # mud.mud.pipeToSocketW.flush()
        # print('Sent AreYouThere packet')
