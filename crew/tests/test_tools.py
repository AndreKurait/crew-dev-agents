import pytest
from unittest.mock import Mock, patch

from src.tools.github_tool import (
    list_open_issues,
    list_open_prs,
    add_issue_comment,
    add_labels,
    create_issue,
    get_repo_contents,
    read_file,
    create_or_update_file,
    create_branch,
    create_pull_request,
    merge_pull_request,
    close_issue,
)


@pytest.fixture
def mock_github():
    with patch("src.tools.github_tool.Github") as mock:
        mock_repo = Mock()
        mock.return_value.get_repo.return_value = mock_repo
        yield mock, mock_repo


def test_list_open_issues(mock_github):
    _, mock_repo = mock_github
    mock_issue = Mock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.body = "Test Body"
    mock_issue.labels = []
    mock_repo.get_issues.return_value = [mock_issue]

    result = list_open_issues("owner/repo")
    assert "Issue #1: Test Issue" in result
    mock_repo.get_issues.assert_called_once_with(state="open")


def test_create_issue(mock_github):
    _, mock_repo = mock_github
    mock_issue = Mock()
    mock_issue.number = 2
    mock_issue.html_url = "https://github.com/owner/repo/issues/2"
    mock_repo.create_issue.return_value = mock_issue

    result = create_issue("owner/repo", "Test Title", "Test Body")
    assert "Created issue #2" in result
    mock_repo.create_issue.assert_called_once_with(
        title="Test Title",
        body="Test Body",
    )


def test_create_branch(mock_github):
    _, mock_repo = mock_github
    mock_ref = Mock()
    mock_ref.object.sha = "abc123"
    mock_repo.get_git_ref.return_value = mock_ref

    result = create_branch("owner/repo", "feature/test-branch")
    assert "Created branch feature/test-branch" in result
    mock_repo.create_git_ref.assert_called_once_with(
        ref="refs/heads/feature/test-branch",
        sha="abc123",
    )


def test_create_pull_request(mock_github):
    _, mock_repo = mock_github
    mock_pr = Mock()
    mock_pr.number = 3
    mock_pr.html_url = "https://github.com/owner/repo/pull/3"
    mock_repo.create_pull.return_value = mock_pr

    result = create_pull_request(
        "owner/repo",
        "feature/test-branch",
        "Test PR",
        "Test PR Body",
    )
    assert "Created PR #3" in result
    mock_repo.create_pull.assert_called_once_with(
        title="Test PR",
        body="Test PR Body",
        head="feature/test-branch",
        base="main",
    )
