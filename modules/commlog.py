
from modules.basemodule import BaseModule


def log(*args, **kwargs):
    print(*args, **kwargs)


class CommLog(BaseModule):
    def __init__(self, mud, commfname: str) -> None:
        super().__init__(mud)
        self.fname = commfname

    def handleGmcp(self, cmd: str, value: dict) -> None:
        if cmd.lower() in ['comm.channel', 'comm.channel.text']:
            channel = value.get('chan') or value['channel']
            msg = value.get('msg') or value['text']
            player = value.get('player') or value['talker']
            log("Got {} with {}".format(cmd, msg))
            self.write(f'[{channel}] {player}: {msg}', channel)

    def write(self, msg: str, channel: str) -> None:
        with open(self.fname.format(channel=channel), 'a') as f:
            f.write(msg + '\n')
