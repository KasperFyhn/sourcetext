import asyncio
import logging

import nest_asyncio
import uvicorn

from sourcetext.server.app import app


class BackgroundServer:
    """A uvicorn server that can run blocking (plain scripts) or backgrounded
    within an already-running event loop (e.g. Jupyter notebooks).

    This class uses nest_asyncio to allow blocking operations within an
    already-running event loop. This enables synchronous start/stop methods that
    block until completion, avoiding race conditions.
    """

    def __init__(self, sessionmaker, port: int = 8001):
        self._sessionmaker = sessionmaker
        self._port = port

        self._server = None
        self._server_task = None

    async def _run_server(self):
        config = uvicorn.Config(app, port=self._port, log_level="info")
        server = uvicorn.Server(config)
        self._server = server

        try:
            app.state.db_sessionmaker = self._sessionmaker  # noqa
            await server.serve()
        except (asyncio.CancelledError, KeyboardInterrupt):
            logging.info("Server stopped")

    def start(self, block: bool | None = None):
        """Start the server.

        Args:
            block: If True, block until the server is stopped (e.g. via ctrl+c) —
                for a plain script. If False, run in the background within an
                already-running event loop (e.g. Jupyter). If None (default),
                auto-detect based on whether an event loop is already running.
        """
        if block is None:
            try:
                asyncio.get_running_loop()
                block = False
            except RuntimeError:
                block = True

        if block:
            try:
                nest_asyncio.apply()
                asyncio.run(self._run_server())
            except KeyboardInterrupt:
                self._server = None
                logging.info("Server stopped by user")
        else:
            # Schedules the server as a task in Jupyter's running event loop
            self._server_task = asyncio.create_task(self._run_server())
            logging.info(f"Server started in background on port {self._port}")

    async def _stop(self):
        if self._server_task is not None and not self._server_task.done():
            self._server.should_exit = True

            try:
                # Wait up to 5 seconds for graceful shutdown
                await asyncio.wait_for(self._server_task, timeout=5.0)
            except asyncio.TimeoutError:
                logging.warning("Server didn't shut down gracefully, forcing cancellation")
                self._server_task.cancel()
                try:
                    await self._server_task
                except asyncio.CancelledError:
                    pass

            self._server = None
            self._server_task = None
            logging.info("Background server stopped")
        else:
            logging.info("No server running")

    def stop(self):
        """Stop the background server. Blocks until the server has fully stopped."""
        # nest_asyncio allows run_until_complete() within Jupyter's running event loop
        nest_asyncio.apply()
        asyncio.get_running_loop().run_until_complete(self._stop())
