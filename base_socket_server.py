import socket
from typing import *


def algorithm(value: int) -> int:
    return value + 42


def handler(client: socket.socket) -> None:
    while True:
        request: bytes = client.recv(100)
        if not request:
            client.close()
            return
        response: int = algorithm(int(request))
        client.send(f'{response}\n'.encode('ascii'))


Address = Tuple[str, int]


def server(address: Address) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    sock.listen(5)
    while True:
        client, client_addr = sock.accept()
        handler(client)


if __name__ == '__main__':
    server(('localhost', 30303))