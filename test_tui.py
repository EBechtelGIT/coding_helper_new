"""Quick test script for the TUI."""

import asyncio
from coding_agent.tui.app import CodingAgentApp


async def main():
    app = CodingAgentApp()
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
