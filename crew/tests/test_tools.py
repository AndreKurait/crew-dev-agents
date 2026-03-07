from unittest.mock import Mock, patch

import pytest
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
        yield mock

@pytest.fixture
def mock_repo(mock_github):
    repo = Mock()
    mock_github.return_value.get_repo.return_value = repo
    return repo

def test_list_open_issues(mock_repo):
    issue1 = Mock(number=1, title="Test Issue")
    mock_repo.get_issues.return_value = [issue1]
    
    result = list_open_issues("owner/repo")
    
    mock_repo.get_issues.assert_called_once_with(state="open")
    assert "#1: Test Issue" in result

def test_create_branch(mock_repo):
    mock_repo.get_branch.return_value.commit.sha = "abc123"
    
    result = create_branch("owner/repo", "test-branch")
    
    mock_repo.create_git_ref.assert_called_once_with(
        ref="refs/heads/test-branch",
        sha="abc123"
    )
    assert "Created branch test-branch" in result

def test_create_pull_request(mock_repo):
    mock_pr = Mock(number=1)
    mock_repo.create_pull.return_value = mock_pr
    
    result = create_pull_request(
        "owner/repo",
        "test-branch",
        "Test PR",
        "PR description",
        [123]
    )
    
    mock_repo.create_pull.assert_called_once_with(
        title="Test PR",
        body="PR description\n\nCloses #123",
        head="test-branch",
        base="main"
    )
    assert "Created PR #1" in result

def test_merge_pull_request(mock_repo):
    mock_pr = Mock()
    mock_repo.get_pull.return_value = mock_pr
    
    result = merge_pull_request("owner/repo", 1)
    
    mock_pr.merge.assert_called_once()
    assert "Merged PR #1" in result
