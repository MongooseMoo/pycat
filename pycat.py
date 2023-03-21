#!/usr/bin/env python3

import importlib
import json
import os
import pprint
import re
import sys
import telnetlib
import threading
from select import select
from types import ModuleType

import mcp
import sentry_sdk
import traceback_with_variables
from modular import ModularClient
from proxy import proxy
from requests.structures import CaseInsensitiveDict

telnetlib.GMCP = b'\xc9'  # type: ignore
telnetlib.MSSP = b'\x46'  # type: ignore

sentry_sdk.init(dsn=os.environ.get('SENTRY_DSN'))

class Session(object):
    def __init__(self, world_module: ModuleType, port: int, arg: str, bindAddr: str, terminate_on_disconnect: bool) -> None:
        self.mud_encoding = 'iso-8859-1'
        self.client_encoding = 'utf-8'
        self.world_module = world_module
        self.arg = arg
        self.world: ModularClient = world_module.getClass()(self, self.arg)
        self.terminate_on_disconnect = terminate_on_disconnect
        self.mcp_debug = False
        try:
            self.socketToPipeR, pipeToSocketW, self.stopFlag, runProxy, self.clients, self.session_state = proxy(bindAddr, port)
            self.pipeToSocketW = os.fdopen(pipeToSocketW, 'wb')
            self.proxyThread = threading.Thread(target=runProxy)
            self.proxyThread.start()
            self.do_connect()
        except Exception as e:
            self.logException(e)
            self.log("Shutting down")
            self.stopFlag.set()
            self.world.quit()
            raise

    def log(self, *args, bar: bool = True, **kwargs) -> None:
        if len(args) == 1 and type(args[0]) == str:
            line = args[0]
        else:
            line = pprint.pformat(args)
        if bar:
            line = "---------\n" + line
        self.show(line.encode(self.client_encoding) + b"\n")

    def logException(self, exception) -> None:
        sentry_sdk.capture_exception(exception)
        traceback_with_variables.print_exc()

    def strip_ansi(self, line):
        return re.sub(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]', '', line)

    def gmcpOut(self, msg):
        if self.telnet:
            self.telnet.sock.sendall(telnetlib.IAC + telnetlib.SB + telnetlib.GMCP + msg.encode(self.mud_encoding) + telnetlib.IAC + telnetlib.SE)

    def iac(self, sock, cmd, option):
        if cmd == telnetlib.WILL:
            if option == telnetlib.GMCP:
                self.log("Enabling GMCP")
                sock.sendall(telnetlib.IAC + telnetlib.DO + option)
                # self.gmcpOut('Core.Hello { "client": "Cizra", "version": "1" }')
                supportables = ['char 1', 'char.base 1', 'char.maxstats 1', 'char.status 1', 'char.statusvars 1', 'char.vitals 1', 'char.worth 1', 'comm 1', 'comm.channel 1', 'comm.tick 1', 'group 1', 'room 1', 'room.info 1']
                self.gmcpOut('Core.Supports.Set ' + str(supportables).replace("'", '"'))
                self.gmcpOut('request room')
                self.gmcpOut('request char')
            elif option == telnetlib.TTYPE:
                self.log("Sending terminal type 'pycat'")
                sock.sendall(telnetlib.IAC + telnetlib.DO + option +
                        telnetlib.IAC + telnetlib.SB + telnetlib.TTYPE + telnetlib.BINARY + b'pycat' + telnetlib.IAC + telnetlib.SE)
            elif option == telnetlib.MSSP:
                print('Enabling MSSP')
                sock.sendall(telnetlib.IAC + telnetlib.DO + option)
            else:
                sock.sendall(telnetlib.IAC + telnetlib.DONT + option)
                print(f'IAC DONT {option}')
        elif cmd == telnetlib.SE:
            data = self.telnet.read_sb_data()
            try:
                if data and data[0] == ord(telnetlib.GMCP):
                    self.handleGmcp(data[1:].decode(self.mud_encoding))
                elif data and data[0] == ord(telnetlib.MSSP):
                    self.session_state['mssp'] = {}
                    for kv in data[2:].split(b'\x01'):
                        if not kv:
                            continue
                        kp = kv.split(b'\x02')
                        self.session_state['mssp'][kp[0].decode()] = kp[1].decode()
                    # print(f"MSSP: {self.session_state['mssp']!r}")
                else:
                    print(repr(data))
            except Exception as e:
                self.logException(e)


    def handleGmcp(self, data):
        # this.that {JSON blob}
        # TODO: move into clients
        space_idx = data.find(' ')
        whole_key = data[:space_idx]
        value_json = data[space_idx + 1:]
        nesting = whole_key.split('.')
        current = self.world.gmcp
        for nest in nesting[:-1]:
            if nest not in current:
                current[nest] = CaseInsensitiveDict()
            current = current[nest]
        lastkey = nesting[-1]
        try:
            val = json.loads(value_json, strict=False)
        except json.decoder.JSONDecodeError:
            val = {"string": value_json}
        if lastkey not in current:
            current[lastkey] = {}
        current[lastkey] = val
        self.world.handleGmcp(whole_key, val)

    def handleMcp(self, line: str) -> bool:
        # http://www.moo.mud.org/mcp2/mcp2.html
        # Regular message:
        #   #$#<message-name> <auth-key> <keyvals>
        # Multiline message:
        # #$#* <datatag> <single-keyval>
        # self.show(line + '\n')

        if self.mcp_debug:
            print(line)
        replace_auth = False
        parts = line.strip().strip('\r').split(' ')
        try:
            if parts[0] == "#$#*":
                # multiline
                self.world.handleMcpMultiline(parts[1], parts[2], ' '.join(parts[3:]))
            elif parts[0] == '#$#:':
                # terminate multikine
                pass
            elif len(parts) < 2:
                # not MCP
                pass
            elif parts[1] == 'edit':
                # Local Edit is built upon MCP 1.0, and doesn't have an auth key
                return False
            elif parts[0] == '#$#mcp' and parts[1] == 'version:':
                if not self.clients:  # nobody connected yet, defer it
                    self.pipeToSocketW.write(('\n' + line + '\n').encode())
                    self.pipeToSocketW.flush()
            else:
                replace_auth = True
                vars = mcp.parse_mcp_vars(parts)
                self.world.handleMcp(parts[0][3:], vars, line)
        except Exception as e:
            print(f'MCP Error: {e}')
            self.logException(e)

        for client in self.clients:
            if client.has_mcp is False:
                continue
            elif client.has_mcp is None:
                # Initialize them
                client.has_mcp = False
                client.write("#$#mcp version: 2.1 to: 2.1\n")
            if replace_auth:
                parts[1] = client.state.get('mcp_key', parts[1])
            client.write(' '.join(parts) + '\n')
        return True

    def connect(self, host: str, port: int) -> telnetlib.Telnet:
        t = telnetlib.Telnet()
        t.set_option_negotiation_callback(self.iac)
        # t.set_debuglevel(1)
        t.open(host, int(port))
        return t

    def send(self, line: str) -> None:
        if not self.telnet:
            self.log("Not Connected.")
            return
        print("> ", line)
        self.telnet.write((line + '\n').encode(self.mud_encoding, errors="replace"))

    def handle_from_telnet(self) -> None:
        try:
            data = self.telnet.read_very_eager()
        except Exception:
            self.log("EOF on telnet")
            self.telnet = None
            if self.terminate_on_disconnect:
                self.world.quit()
                self.stopFlag.set()
                raise
            self.session_state.clear()
            return
        try:
            data = data.decode(self.mud_encoding)
        except UnicodeError as e:
            self.logException(e)
            print("Unicode error:", e)
            print("Data was:", data)
            data = ''

        if not data:
            _ = self.telnet.read_sb_data()
        prn = []
        for line in data.split('\n'):
            if line:
                if line.startswith('#$#'):
                    if self.handleMcp(line):
                        continue
                # elif line.startswith('#$"'):
                #     line = line[3:]
                replacement = None
                try:
                    replacement = self.world.trigger(line.strip())
                except Exception as e:
                    self.logException(e)
                if replacement is not None:
                    line = replacement
            prn.append(line)
        self.show('\n'.join(prn).encode(self.mud_encoding))

    def show(self, line: str | bytes) -> None:
        if isinstance(line, str):
            line = line.encode(self.client_encoding)
        if self.clients:
            for client in self.clients:
                client.write(line)
        self.pipeToSocketW.write(line)
        self.pipeToSocketW.flush()

    def handle_from_pipe(self) -> None:
        data = b''  # to handle partial lines
        try:
            data += os.read(self.socketToPipeR, 4096)
            lines = data.split(b'\n')
            if lines[-1] != b'':  # received partial line, don't process
                data = lines[-1]
            else:
                data = b''
            lines = lines[:-1]  # chop off either the last empty line, or the partial line

            for line in lines:
                line = line.decode(self.client_encoding)
                if line[-1] == '\r':
                    line = line[:-1]
                self.handle_output_line(line)
        except EOFError:
            self.log("EOF in pipe")
            self.stopFlag.set()
            self.world.quit()
            raise


    def handle_output_line(self, data: str):
        """Pre-process data to be sent to the MUD"""
        pprint.pprint(data)
        if data == '#reload' and self.world:
            self.log('Reloading world')
            try:
                state = self.world.state
                gmcp = self.world.gmcp
                self.world.quit()
                self.world_module = importlib.reload(self.world_module)
                self.world = self.world_module.getClass()(self, self.arg)
                self.world.state = state
                self.world.gmcp = gmcp
                if self.telnet is None:
                    self.do_connect()
            except Exception as e:
                self.logException(e)
            return
        elif data.startswith('#connect '):
            world = data[9:]
            self.log(f'Loading `{world}`')
            self.world_module = importlib.import_module('worlds.' + world)
            self.world = self.world_module.getClass()(self, self.arg)
            self.do_connect()
        elif data == '#quit':
            if self.world:
                self.world.quit()
            self.stopFlag.set()
            raise SystemExit()
        elif data.startswith("#$#mcp authentication-key:") and self.world.mcp[0].negotiated:
            try:
                parts = data.strip().split(' ')
                c = [c for c in self.clients if c.state.get('mcp_key') == parts[2]][0]
                print(f'Initializing MCP on {c}')
                for package in self.world.mcp:
                    package.newClient(c)
            except Exception as e:
                self.log("Exception in handle_output_line():", e)
                self.logException(e)
        else:
            handled = False
            try:
                handled = self.world.alias(data)
            except Exception as e:
                self.log("Exception in handle_output_line():", e)
                self.logException(e)
            else:
                if not handled:
                    self.send(data)

    def do_connect(self) -> None:
        host_port = self.world.getHostPort()
        if host_port:
            self.log("Connecting")
            self.telnet = self.connect(*host_port)
            self.log("Connected")
        else:
            self.telnet = None

    def run(self) -> None:
        try:
            while True:
                tsock = []
                if self.telnet:
                    tsock = [self.telnet.get_socket()]

                fds, _, _ = select(tsock + [self.socketToPipeR], [], [])
                for fd in fds:
                    if self.telnet and fd == self.telnet.get_socket():
                        self.handle_from_telnet()
                    elif fd == self.socketToPipeR:
                        self.handle_from_pipe()
        except Exception as e:
            self.log("Exception in run():", e)
            self.logException(e)
        finally:
            self.log("Closing")
            if self.telnet:
                self.telnet.close()
            self.stopFlag.set()

def main():
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: {} worldmodule (without .py) port [arg]".format(sys.argv[0]))
        exit(1)

    world_module = importlib.import_module(sys.argv[1])
    port = int(sys.argv[2])
    arg = sys.argv[3] if len(sys.argv) == 4 else None
    ses = Session(world_module, port, arg)
    ses.run()


if __name__ == '__main__':
    main()
