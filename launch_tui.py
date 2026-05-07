"""Launch the TUI with mock agent for testing."""

import sys
import asyncio

# Mock the necessary components
sys.path.insert(0, '.')

from coding_agent.tui.app import CodingAgentApp
from coding_agent.tui.themes import DEFAULT_THEME


async def main():
    """Run TUI with mock functionality."""
    print("Launching TUI... Press Ctrl+C to exit")
    
    app = CodingAgentApp(theme_name=DEFAULT_THEME)
    
    # Add some test messages
    async def add_test_messages():
        await asyncio.sleep(1)
        app.add_user_message("Hello! Can you help me with this project?")
        await asyncio.sleep(0.5)
        app.add_agent_message(
            "Hello! I'm your coding assistant. I can help you with:"
            "\n\n- Code analysis and review"
            "\n- Adding new features"
            "\n- Fixing bugs"
            "\n- Answering questions about your codebase"
            "\n\nWhat would you like to work on today?"
        )
        app.add_separator()
    
    asyncio.create_task(add_test_messages())
    
    try:
        await app.run_async()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
