"""Test script to run TUI with mock agent."""

import asyncio
import sys
from coding_agent.tui.app import CodingAgentApp
from coding_agent.tui.themes import DEFAULT_THEME


async def main():
    """Run a simple TUI test."""
    print("Starting TUI test with mock agent...")
    
    app = CodingAgentApp(theme_name=DEFAULT_THEME)
    
    # Add a simple message
    async def add_messages():
        await asyncio.sleep(1)
        app.add_user_message("Hello from the test!")
        await asyncio.sleep(0.5)
        app.add_agent_message("Hello! I'm your coding agent. How can I help you today?")
        await asyncio.sleep(0.5)
        app.add_separator()
        await asyncio.sleep(2)
        app.exit()
    
    # Run both tasks
    asyncio.create_task(add_messages())
    await app.run_async()
    print("TUI test completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
