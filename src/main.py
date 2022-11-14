import logging

from h11._connection import DEFAULT_MAX_INCOMPLETE_EVENT_SIZE
from server import Server
from config import Config

STARTUP_FAILURE = 3

logger = logging.getLogger('uvicorn.error')


def run(
    host: str = '127.0.0.1',
    port: int = 8000,
    loop: str = 'auto',
    http: str = 'h11',
    debug: bool = False,
    access_log: bool = True,
    proxy_headers: bool = True,
    backlog: int = 2048,
    h11_max_incomplete_event_size: int = DEFAULT_MAX_INCOMPLETE_EVENT_SIZE,
) -> None:
    config = Config(
        host=host,
        port=port,
        loop=loop,
        http=http,
        debug=debug,
        access_log=access_log,
        proxy_headers=proxy_headers,
        backlog=backlog,
        h11_max_incomplete_event_size=h11_max_incomplete_event_size,
    )
    server = Server(config=config)
    server.run()


if __name__ == '__main__':
    run()  # pragma: no cover
