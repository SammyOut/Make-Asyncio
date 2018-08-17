from collections import deque
import enum
import select
import socket
from typing import *


def algorithm(value: int) -> int:
    return value + 42


async def handler(client: socket.socket) -> None:
    while True:
        request: bytes = await async_recv(client, 100)
        if not request:
            client.close()
            return
        response: int = algorithm(int(request))
        await async_send(client, f'{response}\n'.encode('ascii'))


Address = Tuple[str, int]


async def server(address: Address) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    sock.listen(5)
    while True:
        client, client_addr = await async_accept(sock)
        add_task(handler(client))


class Action(enum.Enum):
    WRITE = enum.auto()
    READ = enum.auto()


class Can:
    def __init__(self, action: Action, target: socket.socket):
        self.action = action
        self.target = target

    def __await__(self):
        yield self.action, self.target


async def async_send(sock: socket.socket, data: bytes) -> int:
    await Can(Action.WRITE, sock)
    return sock.send(data)


async def async_recv(sock: socket.socket, num: int) -> bytes:
    await Can(Action.READ, sock)
    return sock.recv(num)


async def async_accept(sock: socket.socket) -> Tuple[socket.socket, Address]:
    await Can(Action.READ, sock)
    return sock.accept()


Task = TypeVar('Task')
TASKS: Deque[Task] = deque()
WAIT_READ: Dict[socket.socket, Task] = {}
WAIT_WRITE: Dict[socket.socket, Task] = {}


def add_task(task: Task) -> None:
    TASKS.append(task)


def run_tasks() -> None:
    while any((TASKS, WAIT_READ, WAIT_WRITE)):
        while not TASKS:
            readables, writables, _ = select.select(WAIT_READ, WAIT_WRITE, [])
            for sock in readables:
                add_task(WAIT_READ.pop(sock))
            for sock in writables:
                add_task(WAIT_WRITE.pop(sock))

        current_task = TASKS.popleft()
        try:
            action, target = current_task.send(None)
        except StopIteration:
            continue

        if action is Action.READ:
            WAIT_READ[target] = current_task
        elif action is Action.WRITE:
            WAIT_WRITE[target] = current_taskp
        else:
            raise RuntimeError(f'Unexpected action {action!r}')


if __name__ == '__main__':
    add_task(server(('localhost', 30303)))
    run_tasks()
