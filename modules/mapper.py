from modules.basemodule import BaseModule
import mapper.libmapper
import collections
import json
import os
import pprint
import re
import shutil
import time


class Mapper(BaseModule):
    def help(self, args):
        strs = ["Commands:"]
        for cmd in self.commands.keys():
            strs.append(cmd)
        self.log('\n'.join(strs))

    def current(self):
        return self.gmcp['room']['info']['num']

    def here(self, args):
        if args:
            this = int(args[0])
        else:
            this = self.current()

        just_exits = self.m.getRoomExits(this)
        exits = {}
        for dir, tgt in just_exits.items():
            data = self.m.getExitData(this, tgt)
            data = json.loads(data) if data else {}
            exits[dir] = {'dst': tgt, 'data': data}

        self.log('\n' + pprint.pformat({
            'num': this,
            'name': self.m.getRoomName(this),
            'data': self.m.getRoomData(this),
            'coords': self.m.getRoomCoords(this),
            'exits': exits,
            }))

    def path(self, args):
        there = args[0]
        if there in self.data['bookmarks']:
            there = self.data['bookmarks'][there]
        else:
            there = int(there)

        this = self.current()
        if this == there:
            self.log("Already there!")
            return ''
        then = time.time()
        path = self.m.findPath(this, there)
        self.log("{} (found in {} seconds)".format(path, time.time() - then))
        return path

    def go(self, args):
        self.send(self.path(args).replace(';', '\n'))

    def bookmarks(self, args):
        self.log('Bookmarks:\n' + pprint.pformat(self.data['bookmarks']))

    def bookmark(self, args):
        arg = ' '.join(args)
        self.data['bookmarks'][arg] = self.current()
        self.bookmarks([])

    def draw(self, args, sizeX=None, sizeY=None):
        # Draw room at x,y,z. Enumerate exits. For each exit target, breadth-first, figure out its new dimensions, rinse, repeat.
        # █▓▒░
        oneArea = len(args) == 1 and args[0] == 'area'
        if sizeX and sizeY:
            columns, lines = sizeX, sizeY
        else:
            columns, lines = shutil.get_terminal_size((21, 22))

        def adjustExit(x, y, d, prev):
            if d == 'n':
                return x, y-1, '|', '↑'
            if d == 'w':
                return x-1, y, '─', '←'
            if d == 's':
                return x, y+1, '|', '↓'
            if d == 'e':
                return x+1, y, '─', '→'
            if d == 'd':
                if prev == '▲':
                    return x, y, '◆', '◆'
                else:
                    return x, y, '▼', '▼'
            if d == 'u':
                if prev == '▼':
                    return x, y, '◆', '◆'
                else:
                    return x, y, '▲', '▲'
            # TODO: test these in SneezyMUD
            if d == 'nw':
                return x-1, y-1, '/', '/'
            if d == 'sw':
                return x-1, y+1, '\\', '\\'
            if d == 'se':
                return x+1, y+1, '/', '/'
            if d == 'ne':
                return x+1, y-1, '\\', '\\'

        out = []  # NB! indices are out[y][x] because the greater chunks are whole lines
        for _ in range(lines - 1):  # -1 for the next prompt
            out.append([' '] * columns)

        # The only room coordinates that matter are the start room's -- the rest get calculated by tracing paths.
        startX, startY, startZ = self.m.getRoomCoords(self.current())
        centerX, centerY = (columns-1)//2, (lines-1)//2
        data = self.m.getRoomData(self.current())
        area = json.loads(data)['zone']

        roomq = collections.deque()
        roomq.append((centerX, centerY, self.current()))

        visited = set()

        def getExitLen(source, target):
            exitDataS = self.m.getExitData(source, target)
            if not exitDataS:
                return 1
            exitData = json.loads(exitDataS)
            if not exitData or 'len' not in exitData:
                return 1
            return int(exitData['len'])

        def fits(x, y):
            return 0 <= x and x < columns and 0 <= y and y < lines-1

        # TODO: one-way exits
        # TODO: draw doors
        while roomq:
            drawX, drawY, room = roomq.popleft()
            mapX, mapY, mapZ = self.m.getRoomCoords(room)
            visited.add(room)
            # It's possible to keep walking through z layers and end up back on z=initial, which might produce nicer maps -- but we'll have to walk the _whole_ map, or bound by some range.
            out[drawY][drawX] = '█'
            exits = self.m.getRoomExits(room)
            for d, tgt in exits.items():
                if d in ['n', 'e', 's', 'w', 'u', 'd', 'ne', 'se', 'sw', 'nw']:
                    dataS = self.m.getRoomData(tgt)
                    exists = dataS != ''
                    dataD = json.loads(dataS) if exists else {}
                    nextArea = dataD['zone'] if 'zone' in dataD else None
                    sameAreas = oneArea or nextArea == area

                    if not exists or not sameAreas:
                        exitLen = 1
                    else:
                        exitLen = getExitLen(room, tgt)

                    exX = drawX
                    exY = drawY
                    # draw a long exit for beautification
                    for _ in range(exitLen):
                        exX, exY, char, hidden = adjustExit(exX, exY, d, out[drawY][drawX])
                        if fits(exX, exY):
                            # If the map grid element we'd occupy is already occupied, don't go there
                            nextX, nextY, _, _ = adjustExit(exX, exY, d, ' ')  # Adjust again, ie. go one step further in the same direction for the target room
                            # Don't overwrite already drawn areas
                            free = fits(exX, exY) and (not fits(nextX, nextY) or out[nextY][nextX] == ' ') or tgt in visited
                            out[exY][exX] = char if free and exists and sameAreas else hidden

                    nextX, nextY, _, _ = adjustExit(exX, exY, d, ' ')  # Adjust again, ie. go one step further in the same direction for the target room
                    visit = (exists
                            and tgt not in visited
                            and sameAreas
                            and d not in ['u', 'd']
                            and fits(nextX, nextY)
                            and out[nextY][nextX] == ' '
                            )
                    if visit:
                        roomq.append((nextX, nextY, tgt))

        # Special marking for start room:
        if out[centerY][centerX] == '▼':
            out[centerY][centerX] = '▿'
        elif out[centerY][centerX] == '▲':
            out[centerY][centerX] = '▵'
        elif out[centerY][centerX] == '◆':
            out[centerY][centerX] = '◇'
        else:
            out[centerY][centerX] = '░'

        outstr = '\n'.join([''.join(char)  for char in out])
        return outstr

    def quit(self, args=None):
        if args:
            path = args[0]
        else:
            path = self.mapfname
        self.m.setMapData(json.dumps(self.data))
        with open(path, 'w') as f:
            f.write(self.m.serialize())
        self.log("Serialized map to ", path)

    def startExit(self, args):
        self.exitKw = ' '.join(args)
        room = self.gmcp['room']['info']
        self.exitFrom = {}
        self.exitFrom['exits'] = {}
        self.exitFrom['id'] = room['num']
        self.exitFrom['name'] = room['name']
        self.exitFrom['data'] = dict(zone=room['zone'], terrain = room['terrain'])
        exits = {}
        for k, v in room['exits'].items():
            self.exitFrom['exits'][k.lower()] = v
        self.log("Type '#map endexit' when you're in the right room, or #map endexit abort")
        self.send(self.exitKw.replace(';', '\n'))

    def endExit(self, args):
        if len(args) == 1:
            self.log("Aborted.")
            return
        self.exitFrom['exits'][self.exitKw] = self.current()
        self.m.addRoom(
                self.exitFrom['id'],
                self.exitFrom['name'],
                json.dumps(self.exitFrom['data']),
                self.exitFrom['exits'])
        self.exitKw = None

    def exitlen(self, args):
        direction = args[0]
        length = args[1]
        here = self.current()
        exits = self.m.getRoomExits(here)
        if direction.lower() not in exits:
            self.log("No such direction")
            return
        there = exits[direction.lower()]
        data = self.m.getExitData(here, there)
        if data:
            data = json.loads(data)
        else:
            data = {}
        data['len'] = length
        self.m.setExitData(here, there, json.dumps(data))

    def __init__(self, mud, mapfname='default.map'):
        self.mapfname = mapfname
        try:
            with open(self.mapfname, 'r') as f:
                ser = f.read()
            self.m = mapper.libmapper.Map(ser)
            self.data = json.loads(self.m.getMapData())
        except FileNotFoundError:
            self.data = {
                    'bookmarks': {},
                    }
            self.m = mapper.libmapper.Map()

        self.commands = {
                'help': self.help,
                'here': self.here,
                'draw': lambda args: print(self.draw(args)),
                'bookmark': self.bookmark,
                'name': self.bookmark,
                'bookmarks': self.bookmarks,
                'path': self.path,
                'go': self.go,
                'save': self.quit,
                'startexit': self.startExit,
                'endexit': self.endExit,
                'exitlen': self.exitlen,
                }

        self.exitKw = None
        self.exitFrom = None
        super().__init__(mud)

    def alias(self, line):
        words = line.split(' ')

        if words[0] != '#map':
            return

        if len(words) == 1:
            print(self.draw([]))
            return True

        cmd = words[1]
        if cmd in self.commands:
            self.commands[cmd](words[2:])
        else:
            self.help(words[2:])
        return True

    def handleGmcp(self, cmd, value):
        # room.info
        # {'coord': {'cont': 0, 'id': 0, 'x': -1, 'y': -1},
        #   'desc': '',
        #   'details': '',
        #   'exits': {'N': -565511209},
        #   'id': 'Homes#1226',
        #   'name': 'An empty room',
        #   'num': -565511180,
        #   'terrain': 'cave',
        #   'zone': 'Homes'}
        if cmd == 'room.info':
            id = value['num']
            name = value['name']
            data = dict(zone=value['zone'], terrain = value['terrain'])
            exits = self.m.getRoomExits(id)  # retain custom exits
            for k, v in value['exits'].items():
                exits[k.lower()] = v
            self.m.addRoom(id, name, json.dumps(data), exits)

            with open('mapdraw', 'w') as f:
                f.write(self.draw(['area'], 15, 15) + '\n')
