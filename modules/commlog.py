
from modules.basemodule import BaseModule


def log(*args, **kwargs):
    print(*args, **kwargs)


class CommLog(BaseModule):
    def __init__(self, mud, commfname):
        super().__init__(mud)
        self.fname = commfname


    # def drawMapToFile(self):
    #     with open('map.txt', 'wt') as f:
    #         f.write(self.draw())

    def handleGmcp(self, cmd: str, value):
        if cmd.lower() in ['comm.channel', 'comm.channel.text']:
            channel = value.get('chan') or value['channel']
            msg = value.get('msg') or value['text']
            player = value.get('player') or value['talker']
            log("Got {} with {}".format(cmd, msg))
            self.write(f'[{channel}] {player}: {msg}')

    def write(self, msg):
        with open(self.fname, 'a') as f:
            f.write(msg + '\n')
