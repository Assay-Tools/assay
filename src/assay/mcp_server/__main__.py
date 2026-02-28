"""Entry point for `python -m assay.mcp_server`."""

import asyncio

from assay.mcp_server.server import main

asyncio.run(main())
