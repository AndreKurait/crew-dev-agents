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
    with patch('src.tools.github_tool.Github') as mock:
        yield mock

@pytest.fixture
def mock_repo(mock_github):
    repo = Mock()
    mock_github.return_value.get_repo.return_value = repo
    return repo

def test_list_open_issues(mock_repo):
    mock_issue = Mock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.body = "Test Body"
    mock_repo.get_issues.return_value = [mock_issue]

    result = list_open_issues("owner/repo")
    assert "#1: Test Issue" in result
    mock_repo.get_issues.assert_called_once_with(state='open')

def test_create_issue(mock_repo):
    mock_repo.create_issue.return_value.number = 2
    
    result = create_issue("owner/repo", "New Issue", "Issue Body")
    assert "Created issue #2" in result
    mock_repo.create_issue.assert_called_once_with(
        title="New Issue",
        body="Issue Body"
    )

def test_add_labels(mock_repo):
    mock_issue = Mock()
    mock_repo.get_issue.return_value = mock_issue
    
    result = add_labels("owner/repo", 1, ["bug", "good-first-issue"])
    assert "Added labels" in result
    mock_repo.get_issue.assert_called_once_with(1)
    mock_issue.add_to_labels.assert_called_once_with("bug", "good-first-issue")

def test_create_branch(mock_repo):
    mock_repo.get_git_ref.return_value.object.sha = "main-sha"
    
    result = create_branch("owner/repo", "feature/test")
    assert "Created branch feature/test" in result
    mock_repo.create_git_ref.assert_called_once_with(
        ref="refs/heads/feature/test",
        sha="main-sha"
    )

def test_create_pull_request(mock_repo):
    mock_repo.create_pull.return_value.number = 3
    
    result = create_pull_request(
        "owner/repo",
        "feature/test",
        "main",
        "Test PR",
        "PR Body"
    )
    assert "Created PR #3" in result
    mock_repo.create_pull.assert_called_once_with(
        title="Test PR",
        body="PR Body",
        head="feature/test",
        base="main"
    )
