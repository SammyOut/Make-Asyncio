from collections import deque
import functools
import heapq
import enum
import select
import socket
import time
from typing import *

Task = TypeVar('Task')


async def algorithm(value: int) -> int:
    await async_sleep(5)
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
    WAKEUP = enum.auto()


class Can:
    def __init__(self, action: Action, target: Union[socket.socket, float]):
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


async def async_sleep(duration: float) -> None:
    await Can(Action.WAKEUP, duration)


@functools.total_ordering
class TimerHandle:
    def __init__(self, task: Task, due: float):
        self.task = task
        self. due = due

    def __lt__(self, other):
        return self.due < other.due

    def __eq__(self, other):
        return self.due == other.due


TASKS: Deque[Task] = deque()
WAIT_READ: Dict[socket.socket, Task] = {}
WAIT_WRITE: Dict[socket.socket, Task] = {}
WAIT_WAKEUP: List[TimerHandle] = []

MAX_TIMEOUT = 24 * 3600


def add_task(task: Task) -> None:
    TASKS.append(task)


def run_tasks() -> None:
    while any((TASKS, WAIT_READ, WAIT_WRITE, WAIT_WAKEUP)):
        now = time.monotonic()
        while not TASKS:
            if WAIT_WAKEUP:
                timeout = max(0, WAIT_WAKEUP[0].due - now)
                timeout = min(MAX_TIMEOUT, timeout)
            else:
                timeout = MAX_TIMEOUT
            readables, writables, _ = select.select(WAIT_READ, WAIT_WRITE, [], timeout)
            now = time.monotonic()
            for sock in readables:
                add_task(WAIT_READ.pop(sock))
            for sock in writables:
                add_task(WAIT_WRITE.pop(sock))
            while WAIT_WAKEUP:
                heapq.heappop(WAIT_WAKEUP)
                timer_handle = WAIT_WAKEUP[0]
                if timer_handle.due >= now:
                    break
                add_task(timer_handle.task)
                heapq.heappop(WAIT_WAKEUP)

        current_task = TASKS.popleft()
        try:
            action, target = current_task.send(None)
        except StopIteration:
            continue

        if action is Action.READ:
            WAIT_READ[target] = current_task
        elif action is Action.WRITE:
            WAIT_WRITE[target] = current_task
        elif action is Action.WAKEUP:
            heapq.heappush(WAIT_WAKEUP, TimerHandle(current_task, now + target))
        else:
            raise RuntimeError(f'Unexpected action {action!r}')


if __name__ == '__main__':
    add_task(server(('localhost', 30303)))
    run_tasks()
