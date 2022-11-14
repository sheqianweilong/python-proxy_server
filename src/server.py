from config import Config
import logging
import asyncio
import sys
import functools
from typing import Set, List, Tuple

logger = logging.getLogger("Proxy server")


class ServerState:
    """
    Shared servers state that is available between all protocol instances.
    """

    def __init__(self) -> None:
        self.total_requests = 0
        self.connections: Set = set()
        self.tasks: Set[asyncio.Task] = set()
        self.default_headers: List[Tuple[bytes, bytes]] = []


class Server:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.server_state = ServerState()
        self.started = False
        self.should_exit = False
        self.force_exit = False
        self.last_notified = 0.0

    def run(self) -> None:
        # self.config.setup_event_loop()
        return asyncio.run(self.serve())

    async def serve(self) -> None:
        await self.startup()
        if self.should_exit:
            return
        await self.main_loop()

    async def startup(self) -> None:
        config = self.config
        create_protocol = functools.partial(
            config.http_protocol_class, config=config, server_state=self.server_state
        )
        loop = asyncio.get_running_loop()

        try:
            server = await loop.create_server(
                create_protocol,
                host=config.host,
                port=config.port,
                backlog=config.backlog,
            )
        except OSError as exc:
            logger.error(exc)
            sys.exit(1)
        assert server.sockets is not None
        self.servers = [server]
        self.started = True

    async def main_loop(self) -> None:
        while True:
            await asyncio.sleep(0.1)
