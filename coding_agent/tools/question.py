"""Question tool - lets the LLM ask the user structured questions.

Matches opencode's `question` tool that renders a modal with options
and returns the user's selection.
"""

import json
from typing import Optional

from langchain_core.tools import Tool
from pydantic import BaseModel, Field


_question_callback = None


def set_question_callback(callback):
    """Set the callback for asking questions.

    The callback receives (header, question, options, multiple) and
    returns a list of selected labels or a string for custom input.
    """
    global _question_callback
    _question_callback = callback


def question_func(
    questions: str,
    header: str = "",
    options: Optional[list] = None,
    multiple: bool = False,
) -> str:
    """Ask the user a question with optional choices.

    Args:
        questions: The question text to ask the user.
        header: Short label (max 30 chars) for the question category.
        options: List of option strings the user can pick from.
        multiple: Whether the user can select multiple options.

    Returns:
        The user's answer as a string.
    """
    global _question_callback
    if _question_callback:
        result = _question_callback(
            header=header or "Question",
            question=questions,
            options=options or [],
            multiple=multiple,
        )
        if isinstance(result, list):
            return json.dumps(result)
        return str(result)
    return "Error: Question callback not available"


question_tool = Tool(
    name="question",
    description="""Ask the user a question with optional predefined choices.

Use this when you need to:
- Gather user preferences or requirements
- Clarify ambiguous instructions
- Get decisions on implementation choices
- Offer choices about what direction to take

Args:
    questions: The question text.
    header: Short label (max 30 chars).
    options: Optional list of predefined choices.
    multiple: If True, allow selecting multiple options.
""",
    func=question_func,
)


def get_question_tool():
    return question_tool
