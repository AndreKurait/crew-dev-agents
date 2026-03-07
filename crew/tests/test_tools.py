"""Tests for GitHub tools module."""
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
    with patch('github.Github') as mock:
        yield mock

@pytest.fixture
def mock_repo(mock_github):
    repo = Mock()
    mock_github.return_value.get_repo.return_value = repo
    return repo

def test_list_open_issues(mock_repo):
    """Should return list of open issues."""
    mock_issue = Mock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.labels = [Mock(name="bug")]
    mock_repo.get_issues.return_value = [mock_issue]
    
    issues = list_open_issues("owner/repo")
    assert len(issues) == 1
    assert issues[0]["number"] == 1
    assert issues[0]["title"] == "Test Issue"
    assert issues[0]["labels"] == ["bug"]

def test_create_issue(mock_repo):
    """Should create new issue with title and body."""
    mock_issue = Mock(number=2)
    mock_repo.create_issue.return_value = mock_issue

    issue_num = create_issue(
        "owner/repo",
        title="New Issue",
        body="Issue description"
    )
    assert issue_num == 2
    mock_repo.create_issue.assert_called_once_with(
        title="New Issue",
        body="Issue description"
    )

def test_add_labels(mock_repo):
    """Should add labels to an issue."""
    mock_issue = Mock()
    mock_repo.get_issue.return_value = mock_issue

    add_labels("owner/repo", issue_number=1, labels=["bug", "help wanted"])
    
    mock_repo.get_issue.assert_called_once_with(1)
    mock_issue.add_to_labels.assert_called_once_with("bug", "help wanted")

def test_create_branch(mock_repo):
    """Should create new branch from main."""
    mock_ref = Mock()
    mock_repo.get_git_ref.return_value = mock_ref
    mock_ref.object.sha = "main-sha"

    create_branch("owner/repo", "feature/test")

    mock_repo.get_git_ref.assert_called_once_with("heads/main")
    mock_repo.create_git_ref.assert_called_once_with(
        ref="refs/heads/feature/test",
        sha="main-sha"
    )

def test_create_pull_request(mock_repo):
    """Should create PR from branch to main."""
    mock_pr = Mock(number=3)
    mock_repo.create_pull.return_value = mock_pr

    pr_num = create_pull_request(
        "owner/repo",
        title="Test PR",
        body="PR description",
        branch="feature/test",
        base="main"
    )

    assert pr_num == 3
    mock_repo.create_pull.assert_called_once_with(
        title="Test PR",
        body="PR description",
        head="feature/test",
        base="main"
    )
