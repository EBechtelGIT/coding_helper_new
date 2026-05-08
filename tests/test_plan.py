"""Tests for the plan data model and parser."""

from coding_agent.plan import Plan, parse_plan_from_text, FileChange


SAMPLE_PLAN = """## Goal
Add user authentication to the API

## Current State
The API has no auth middleware yet. Routes are unprotected.

## Approach
- Install JWT library
- Create auth middleware
- Add login endpoint
- Protect routes

## Files to Modify
- modify: src/middleware/auth.py
- create: src/routes/login.py
- modify: src/app.py

## Risks
- Token expiration handling
- Password storage security

## Open Questions
- Which JWT library to use?
- Token expiry duration?
"""


def test_parse_full_plan():
    plan = parse_plan_from_text(SAMPLE_PLAN)
    assert plan.goal == "Add user authentication to the API"
    assert "no auth middleware yet" in plan.current_state.lower()
    assert len(plan.approach) == 4
    assert plan.approach[0] == "Install JWT library"
    assert len(plan.files_to_modify) == 3
    assert plan.files_to_modify[0].path == "src/middleware/auth.py"
    assert plan.files_to_modify[0].change_type == "modify"
    assert plan.files_to_modify[1].change_type == "create"
    assert len(plan.risks) == 2
    assert len(plan.open_questions) == 2


def test_parse_minimal_plan():
    text = "## Goal\nDo the thing\n## Approach\n- Step 1"
    plan = parse_plan_from_text(text)
    assert plan.goal == "Do the thing"
    assert len(plan.approach) == 1
    assert plan.approach[0] == "Step 1"
    assert plan.current_state == ""
    assert plan.files_to_modify == []


def test_empty_plan():
    plan = parse_plan_from_text("Hello world")
    assert plan.is_empty()


def test_plan_to_prompt_block():
    plan = Plan(
        goal="Fix the bug",
        approach=["Find the issue", "Apply fix", "Test"],
        files_to_modify=[FileChange(path="src/main.py", change_type="modify")],
    )
    block = plan.to_prompt_block()
    assert "Fix the bug" in block
    assert "Find the issue" in block
    assert "src/main.py" in block


def test_plan_is_empty():
    empty = Plan()
    assert empty.is_empty()
    non_empty = Plan(goal="Something")
    assert not non_empty.is_empty()


def test_plan_to_dict():
    plan = Plan(
        goal="Test",
        approach=["A", "B"],
        risks=["Risk 1"],
    )
    d = plan.to_dict()
    assert d["goal"] == "Test"
    assert d["approach"] == ["A", "B"]
    assert d["risks"] == ["Risk 1"]
    assert "raw_text" in d


def test_parse_without_section_headers():
    text = "Just some text with no plan structure"
    plan = parse_plan_from_text(text)
    assert plan.goal == ""
    assert plan.approach == []


def test_file_change_dataclass():
    fc = FileChange(path="test.py", change_type="create")
    assert fc.path == "test.py"
    assert fc.change_type == "create"
