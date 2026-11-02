import json
from types import SimpleNamespace
from unittest.mock import Mock

from github import GithubException
import pytest

from src.tools import github_tool as tools


@pytest.fixture
def repo(monkeypatch):
    repo = Mock(default_branch="trunk")
    client = Mock()
    client.get_repo.return_value = repo
    monkeypatch.setattr(tools, "_get_github", lambda: client)
    monkeypatch.setenv("REPO_URL", "https://github.com/example/test-repo")
    return repo


def test_lists_issues_without_pull_requests(repo):
    repo.get_issues.return_value = [
        SimpleNamespace(pull_request=object()),
        SimpleNamespace(pull_request=None, number=2, title="Issue", body=None,
                        labels=[SimpleNamespace(name="bug")]),
    ]
    assert json.loads(tools.list_open_issues.run(limit=1)) == [
        {"number": 2, "title": "Issue", "body": "", "labels": ["bug"]}
    ]


def test_creates_issue_with_labels(repo):
    repo.create_issue.return_value = SimpleNamespace(number=3, html_url="https://example.test/issues/3")
    assert json.loads(tools.create_issue.run(title="Title", body="Body", labels="bug, help wanted"))["number"] == 3
    repo.create_issue.assert_called_once_with(title="Title", body="Body", labels=["bug", "help wanted"])


def test_adds_labels(repo):
    tools.add_labels.run(issue_number=2, labels="bug, enhancement")
    repo.get_issue.assert_called_once_with(2)
    repo.get_issue.return_value.add_to_labels.assert_called_once_with("bug", "enhancement")


def test_branch_uses_repository_default(repo):
    repo.get_git_ref.return_value.object.sha = "base-sha"
    tools.create_branch.run(branch_name="auto/fix")
    repo.get_git_ref.assert_called_once_with("heads/trunk")
    repo.create_git_ref.assert_called_once_with("refs/heads/auto/fix", "base-sha")


@pytest.mark.parametrize("branch", ["", "trunk", "refs/heads/trunk"])
def test_file_tool_rejects_implicit_or_default_branch(repo, branch):
    assert tools.create_or_update_file.run(path="test.txt", content="content", branch=branch).startswith("Error:")
    repo.get_contents.assert_not_called()
    repo.update_file.assert_not_called()
    repo.create_file.assert_not_called()


def test_file_tool_only_treats_404_as_missing(repo):
    repo.get_contents.side_effect = GithubException(403, {"message": "Forbidden"})
    assert tools.create_or_update_file.run(path="test.txt", content="content", branch="auto/fix").startswith("Error:")
    repo.create_file.assert_not_called()


def test_file_tool_can_create_an_empty_file(repo):
    repo.get_contents.side_effect = GithubException(404, {"message": "Not Found"})
    repo.create_file.return_value = {"commit": SimpleNamespace(sha="new-sha")}
    assert json.loads(tools.create_or_update_file.run(path="empty.txt", content="", branch="auto/fix"))["action"] == "created"
    repo.create_file.assert_called_once_with("empty.txt", "auto update", "", branch="auto/fix")


def test_pull_request_is_draft_and_uses_default_branch(repo):
    repo.create_pull.return_value = SimpleNamespace(number=4, html_url="https://example.test/pull/4")
    tools.create_pull_request.run(title="Title", body="Body", head_branch="auto/fix")
    repo.create_pull.assert_called_once_with(title="Title", body="Body", head="auto/fix", base="trunk", draft=True)
