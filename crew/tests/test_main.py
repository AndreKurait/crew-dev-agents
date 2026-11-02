import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

from github import GithubException
import pytest

from src import main


@pytest.fixture
def plan():
    return {
        "improvement": "Fix a bug",
        "branch_name": "auto/fix",
        "files": [{"path": "test.txt", "content": "new content", "message": "Fix a bug"}],
        "pr_title": "Fix a bug",
        "pr_body": "Description",
    }


@pytest.fixture
def repo(monkeypatch):
    repo = Mock(default_branch="trunk")
    repo.get_git_ref.return_value.object.sha = "base-sha"
    repo.get_contents.return_value = SimpleNamespace(sha="old-sha")
    repo.create_pull.return_value.number = 42
    monkeypatch.setattr(main, "get_repo", lambda: repo)
    return repo


def test_execution_leaves_draft_for_review_without_merging_or_closing(repo, plan):
    plan["close_issues"] = [123]  # Old model output must not authorize closing issues.
    assert main.execute_plan(plan) == 42
    repo.get_git_ref.assert_called_once_with("heads/trunk")
    repo.update_file.assert_called_once_with("test.txt", "Fix a bug", "new content", "old-sha", branch="auto/fix")
    repo.create_pull.assert_called_once_with(
        title="Fix a bug", body="Description", head="auto/fix", base="trunk", draft=True
    )
    repo.create_pull.return_value.merge.assert_not_called()
    repo.get_issue.assert_not_called()


@pytest.mark.parametrize("change", [
    {"branch_name": "main"},
    {"branch_name": "auto/../main"},
    {"files": []},
    {"files": [{"path": "../outside", "content": "bad"}]},
    {"files": [{"path": ".git/config", "content": "bad"}]},
    {"files": [{"path": "test.txt", "content": 123}]},
    {"files": [{"path": "test.txt", "content": "a"}, {"path": "test.txt", "content": "b"}]},
])
def test_invalid_plan_fails_before_repository_access(monkeypatch, plan, change):
    get_repo = Mock(side_effect=AssertionError("No repository access expected"))
    monkeypatch.setattr(main, "get_repo", get_repo)
    plan.update(deepcopy(change))
    with pytest.raises(ValueError):
        main.execute_plan(plan)
    get_repo.assert_not_called()


def test_permission_failure_does_not_fall_back_to_create(repo, plan):
    repo.get_contents.side_effect = GithubException(403, {"message": "Forbidden"})
    with pytest.raises(GithubException):
        main.execute_plan(plan)
    repo.create_file.assert_not_called()
    repo.create_pull.assert_not_called()


def test_main_reports_failure_to_scheduler(monkeypatch):
    monkeypatch.setenv("REPO_URL", "https://github.com/example/test-repo")
    monkeypatch.setattr(main, "gather_context", Mock(side_effect=RuntimeError("offline failure")))
    assert main.main() == 1


def test_main_rejects_missing_target(monkeypatch):
    monkeypatch.delenv("REPO_URL", raising=False)
    assert main.main() == 1


def test_configured_crew_exposes_no_merge_or_close_tools(monkeypatch):
    from src import crew

    agent = Mock()
    monkeypatch.setattr(crew, "LLM", Mock())
    monkeypatch.setattr(crew, "Agent", agent)
    monkeypatch.setattr(crew, "Task", Mock())
    monkeypatch.setattr(crew, "Crew", Mock())
    crew.build_crew("https://github.com/example/test-repo")
    for call in agent.call_args_list:
        assert all(tool.name not in {"merge_pull_request", "close_issue"} for tool in call.kwargs["tools"])


def test_open_draft_and_merged_history_reach_planner_input(repo, plan, monkeypatch):
    import crewai

    repo.get_issues.return_value = []
    draft = SimpleNamespace(number=7, title="Pending draft improvement", draft=True)
    open_pr = SimpleNamespace(number=8, title="Pending reviewed improvement", draft=False)
    merged = SimpleNamespace(number=9, title="Previously merged improvement", merged=True)
    unmerged = SimpleNamespace(number=10, title="Closed without merging", merged=False)
    repo.get_pulls.side_effect = lambda *, state, **kwargs: (
        [draft, open_pr] if state == "open" else [merged, unmerged]
    )
    llm = Mock()
    llm.call.return_value = json.dumps(plan)
    monkeypatch.setattr(crewai, "LLM", Mock(return_value=llm))

    context = main.gather_context()
    assert context["recent_prs"] == [{"number": 9, "title": merged.title}]
    assert context["open_prs"] == [
        {"number": 7, "title": draft.title, "draft": True},
        {"number": 8, "title": open_pr.title, "draft": False},
    ]
    assert main.ask_llm_for_plan(context) == plan
    prompt = llm.call.call_args.args[0][0]["content"]
    assert draft.title in prompt
    assert open_pr.title in prompt
    assert '"draft": true' in prompt
    assert merged.title in prompt
    assert unmerged.title not in prompt
    repo.create_pull.assert_not_called()
