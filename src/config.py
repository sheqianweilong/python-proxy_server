import asyncio
import logging
import logging.config
import socket
import sys
from typing import (
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from h11._connection import DEFAULT_MAX_INCOMPLETE_EVENT_SIZE


from typing import Literal


from importer import import_from_string

HTTPProtocolType = Literal["auto", "h11", "httptools"]

HTTP_PROTOCOLS: Dict = {
    "h11": "protocols.http.h11_impl:H11Protocol",
}
LOOP_SETUPS: Dict = {
    "none": None,
    "auto": "uvicorn.loops.auto:auto_loop_setup",
    "asyncio": "uvicorn.loops.asyncio:asyncio_setup",
    "uvloop": "uvicorn.loops.uvloop:uvloop_setup",
}


logger = logging.getLogger("uvicorn.error")


class Config:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        loop: str = "auto",
        http: str = "h11",
        log_level: Optional[Union[str, int]] = None,
        access_log: bool = True,
        use_colors: Optional[bool] = None,
        debug: bool = False,
        proxy_headers: bool = True,
        backlog: int = 2048,
        timeout_keep_alive: int = 5,
        h11_max_incomplete_event_size: int = DEFAULT_MAX_INCOMPLETE_EVENT_SIZE,
    ):
        self.host = host
        self.port = port
        self.loop = loop
        self.http = http
        self.log_level = log_level
        self.access_log = access_log
        self.use_colors = use_colors
        self.debug = debug
        self.proxy_headers = proxy_headers
        self.backlog = backlog
        self.timeout_keep_alive = timeout_keep_alive
        self.encoded_headers: List[Tuple[bytes, bytes]] = []
        self.h11_max_incomplete_event_size = h11_max_incomplete_event_size

        self.load()

    def load(self) -> None:

        if isinstance(self.http, str):
            http_protocol_class = import_from_string(HTTP_PROTOCOLS[self.http])
            self.http_protocol_class: Type[asyncio.Protocol] = http_protocol_class
        else:
            self.http_protocol_class = self.http

    def setup_event_loop(self) -> None:
        loop_setup: Optional[Callable] = import_from_string(
            LOOP_SETUPS[self.loop])
        if loop_setup is not None:
            loop_setup()

    def bind_socket(self) -> socket.socket:
        family = socket.AF_INET
        sock = socket.socket(family=family)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.host, self.port))
        except OSError as exc:
            logger.error(exc)
            sys.exit(1)
        sock.set_inheritable(True)
        return sock
