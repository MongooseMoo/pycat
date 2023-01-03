#!/usr/bin/env python3

import os
import socket
import threading
from select import select

SINGLE_CLIENT = False

# returns anonymous pipes (readableFromClient, writableToClient)
def proxy(bindAddr, listenPort):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((bindAddr, listenPort))
    sock.listen(5)
    socketToPipeR, socketToPipeW = os.pipe()
    pipeToSocketR, pipeToSocketW = os.pipe()
    stop = threading.Event()
    print(f'Listening on {bindAddr}:{listenPort}')

    return socketToPipeR, pipeToSocketW, stop, lambda: serve(socketToPipeW, pipeToSocketR, sock, stop)

def serve(socketToPipeW: int, pipeToSocketR: int, sock: socket.socket, stop: threading.Event):
    socketToPipeW = os.fdopen(socketToPipeW, 'wb')

    clientSockets = []
    addr = None

    pipeToSocketBuffer: list[bytes] = []

    while not stop.is_set():
        fds, _, _ = select([sock, pipeToSocketR] + clientSockets, [], [])
        for fd in fds:
            if fd == sock:
                print("new client")
                if SINGLE_CLIENT and clientSockets:  # If the user doesn't want to be connected with two clients at once.
                    print("booting old client")
                    clientSockets[0].sendall(b"Superseded. Bye!")
                    clientSockets[0].close()
                    clientSockets = []
                clientSocket, addr = sock.accept()
                clientSockets.append(clientSocket)
                for item in pipeToSocketBuffer:
                    clientSocket.sendall(item)
                pipeToSocketBuffer = []
            elif fd in clientSockets:
                try:
                    data = fd.recv(4096)
                    if not data:  # disconnect
                        fd.close()
                        clientSockets.remove(fd)
                        print("socket disconnected")
                    else:
                        socketToPipeW.write(data)  # TODO: partial writes?
                        socketToPipeW.flush()
                except TimeoutError:
                    fd.close()
                    clientSockets.remove(fd)
                    print("socket timed out")
                except OSError as e:
                    fd.close()
                    clientSockets.remove(fd)
                    print(e)

            elif fd == pipeToSocketR:
                data = os.read(pipeToSocketR, 4096)
                if not data:
                    print("EOF from pipe")
                    break
                if clientSockets:
                    for clientSocket in clientSockets:
                        clientSocket.sendall(data)  # TODO: partial writes?
                else:
                    pipeToSocketBuffer.append(data)
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
