import asyncio
from typing import Optional, Tuple, Union, cast
import h11

from protocols.utils import (
    ceil_timeout,
    get_local_addr,
    get_remote_addr,
    is_ssl,
)
from config import Config


from typing import Literal

from server import ServerState
import functools

H11Event = Union[
    h11.Request,
    h11.InformationalResponse,
    h11.Response,
    h11.Data,
    h11.EndOfMessage,
    h11.ConnectionClosed,
]


class ProxyProtocol(asyncio.Protocol):

    def __init__(self, client_conn: asyncio.Transport) -> None:
        super().__init__()
        self.client_conn = client_conn

    def eof_received(self) -> None:
        pass

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        tr = cast(asyncio.Transport, transport)
        self.transport = tr

    def data_received(self, data: bytes) -> None:
        self.client_conn.write(data=data)


class H11Protocol(asyncio.Protocol):
    def __init__(
        self,
        config: Config,
        server_state: ServerState,
        _loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self.config = config
        self.loop = _loop or asyncio.get_event_loop()
        self.conn = h11.Connection(
            h11.SERVER, config.h11_max_incomplete_event_size)

        # Timeouts
        self.timeout_keep_alive_task: Optional[asyncio.TimerHandle] = None
        self.timeout_keep_alive = config.timeout_keep_alive

        # Shared server state
        self.server_state = server_state
        self.connections = server_state.connections
        self.tasks = server_state.tasks
        self.default_headers = server_state.default_headers

        # Per-connection state
        self.transport: asyncio.Transport = None  # type: ignore[assignment]
        self.server: Optional[Tuple[str, int]] = None
        self.client: Optional[Tuple[str, int]] = None
        self.scheme: Optional[Literal["http", "https"]] = None

        # self.headers: List[Tuple[bytes, bytes]] = None

    # Protocol interface
    def connection_made(  # type: ignore[override]
        self, transport: asyncio.Transport
    ) -> None:
        self.connections.add(self)

        self.transport = transport
        self.server = get_local_addr(transport)
        self.client = get_remote_addr(transport)
        self.scheme = "https" if is_ssl(transport) else "http"

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self.connections.discard(self)
        if exc is None:
            self.transport.close()

    def eof_received(self) -> None:
        pass

    def data_received(self, data: bytes) -> None:
        self.conn.receive_data(data)
        self.handle_events(data)

    def handle_events(self, data) -> None:
        while True:
            try:
                event = self.conn.next_event()
            except h11.RemoteProtocolError:
                return
            event_type = type(event)

            if event_type is h11.NEED_DATA:
                break

            elif event_type is h11.Request:
                loop = asyncio.get_event_loop()
                # 可以将该函数移到代理协议中完成

                async def proxy(event):
                    self.headers = {key.lower(): value for key,
                                    value in event.headers}
                    event = cast(h11.Request, event)
                    host_info = self.headers[b"host"].split(b":")
                    # 简单地先写死
                    # todo 补充https协议
                    if len(host_info) == 1:
                        host, port = host_info[0], 80
                    elif len(host_info) == 2:
                        host, port = host_info
                    # (family, sockettype, _, _,target_addr) = socket.getaddrinfo(host, port)[0]
                    # 将客户端连接以偏函数的方式传到代理协议中,在代理协议的事件处理中完成后续的转发内容
                    factory = functools.partial(
                        ProxyProtocol, client_conn=self.transport)
                    try:
                        # connection timeout
                        async with ceil_timeout(50):
                            # 连接远程服务器,并把客户端内容转发服务器
                            _, protocol = await loop.create_connection(protocol_factory=factory, host=host, port=port)
                            transport = cast(asyncio.Transport, protocol.transport)  # noqa
                            transport.write(data=data)
                    except asyncio.TimeoutError as exc:
                        raise exc

                loop.create_task(proxy(event=event))
                break
