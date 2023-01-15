#!/usr/bin/env python3

import collections
import os
import socket
import threading
from select import select
from typing import Any, Callable

import attrs

SINGLE_CLIENT = False


@attrs.define(slots=False)
class Client():
    fd: socket.socket
    addr: tuple[str, int]
    oob_out: tuple[int, int]
    has_gmcp: bool | None = None
    has_mcp: bool | None = None
    state: dict = attrs.field(factory=dict)

    pipe_write = None

    def write(self, line: bytes | str) -> None:
        if isinstance(line, str):
            line = line.encode('utf-8')
        if self.pipe_write is None:
            self.pipe_write = os.fdopen(self.oob_out[1], 'wb')
        self.pipe_write.write(line)
        self.pipe_write.flush()

    def handle_inbound_mcp(self, line: bytes) -> bytes:
        parts = line.split(b' ')
        if parts[0] == b'#$#mcp' and parts[1] == b'authentication-key:':
            self.has_mcp = True
            self.state["mcp_key"] = parts[2].decode('utf-8')
        return line

# returns anonymous pipes (readableFromClient, writableToClient)
def proxy(bindAddr: str, listenPort: int) -> tuple[int, int, threading.Event, Callable, list[Client], dict[str, Any]]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((bindAddr, listenPort))
    sock.listen(5)
    socketToPipeR, socketToPipeW = os.pipe()
    pipeToSocketR, pipeToSocketW = os.pipe()
    stop = threading.Event()
    print(f'Listening on {bindAddr}:{listenPort}')

    session_state = {}
    clients: list[Client] = []

    return socketToPipeR, pipeToSocketW, stop, lambda: serve(socketToPipeW, pipeToSocketR, sock, stop, clients, session_state), clients, session_state

def serve(socketToPipeW: int, pipeToSocketR: int, sock: socket.socket, stop: threading.Event, clients: list[Client], session_state: dict[str, Any]) -> None:
    socketToPipeW = os.fdopen(socketToPipeW, 'wb')

    clientSockets: list[socket.socket] = []
    clientStates: dict[socket.socket, Client] = {}
    clientPipes: list[int] = []

    pipeToSocketBuffer: list[bytes] = []
    lastTen = collections.deque(maxlen=40)

    def remove_socket(fd: Any) -> Client:
        fd.close()
        clientSockets.remove(fd)
        c = clientStates[fd]
        clients.remove(c)
        if c.pipe_write:
            c.pipe_write.close()
        clientPipes.remove(c.oob_out[0])
        return c

    def accept(sock: socket.socket) -> None:
        print("new client")
        if SINGLE_CLIENT and clientSockets:  # If the user doesn't want to be connected with two clients at once.
            print("booting old client")
            clientSockets[0].sendall(b"Superseded. Bye!")
            clientSockets[0].close()
            clientSockets.clear()
        clientSocket, addr = sock.accept()
        clientSockets.append(clientSocket)
        state = Client(clientSocket, addr, os.pipe())
        clients.append(state)
        clientStates[clientSocket] = state
        clientPipes.append(state.oob_out[0])
        for item in pipeToSocketBuffer or lastTen:
            clientSocket.sendall(item)
        pipeToSocketBuffer.clear()

    while not stop.is_set():
        fds, _, _ = select([sock, pipeToSocketR] + clientSockets + clientPipes, [], [])
        for fd in fds:
            if fd == sock:
                accept(sock)
            elif fd in clientSockets:
                try:
                    data: bytes = fd.recv(4096)
                    if not data:  # disconnect
                        remove_socket(fd)
                        print("socket disconnected")
                    else:
                        if data.startswith(b'#$#'):
                            s = clientStates[fd]
                            data = s.handle_inbound_mcp(data)
                            if 'mcp_key' not in session_state and 'mcp_key' in s.state:
                                session_state['mcp_key'] = s.state['mcp_key']
                                # todo replace client key with session key
                            elif (ckey := s.state.get('mcp_key')) != (skey := session_state.get('mcp_key')) and ckey and skey:
                                data.replace(ckey.encode('utf-8'), skey.encode('utf-8'))
                        socketToPipeW.write(data)  # TODO: partial writes?
                        socketToPipeW.flush()
                except TimeoutError:
                    remove_socket(fd)
                    print("Socket timed out")
                except OSError as e:
                    remove_socket(fd)
                    print(e)

            elif fd == pipeToSocketR:
                data = os.read(pipeToSocketR, 4096)
                if not data:
                    print("EOF from pipe")
                    break
                lastTen.append(data)
                if clientSockets:
                    for clientSocket in list(clientSockets):
                        try:
                            clientSocket.sendall(data)  # TODO: partial writes?
                        except TimeoutError:
                            remove_socket(clientSocket)
                            print("client timed out")
                        except OSError as e:
                            remove_socket(clientSocket)
                            print(e)
                else:
                    pipeToSocketBuffer.append(data)
            elif fd in clientPipes:
                state = [c for c in clientStates.values() if c.oob_out[0] == fd][0]
                data = os.read(fd, 4096)
                state.fd.sendall(data)
    print("Gracefully shutting down in serve")

if __name__ == "__main__":
    def echo(socketToPipeR, pipeToSocketW, stopFlag):
        pipeToSocketW = os.fdopen(pipeToSocketW, 'wb')
        try:
            while not stopFlag.is_set():
                data = os.read(socketToPipeR, 4096)
                print(b"Got %d, sleeping" % (len(data)))
                import time
                time.sleep(1)
                print(b"Echoing %d" % (len(data)))
                pipeToSocketW.write(data)
                pipeToSocketW.flush()
        except KeyboardInterrupt:
            stopFlag.set()
        print("Gracefully shutting down in echo")

    socketToPipeR, pipeToSocketW, stopFlag, work = proxy('::1', 1234)
    echoThr = threading.Thread(target=echo, args=[socketToPipeR, pipeToSocketW, stopFlag])
    echoThr.start()
    try:
        work()
    except KeyboardInterrupt:
        stopFlag.set()
    echoThr.join()
