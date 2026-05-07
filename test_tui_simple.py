"""Test the TUI by running it briefly."""

import asyncio
import signal
from coding_agent.tui.app import CodingAgentApp


async def run_test():
    app = CodingAgentApp()
    
    # Schedule a stop after 2 seconds
    async def stop_app():
        await asyncio.sleep(2)
        app.exit()
    
    asyncio.create_task(stop_app())
    
    try:
        await app.run_async()
        print("TUI ran successfully!")
    except Exception as e:
        print(f"Error running TUI: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_test())
