from unittest.mock import patch, MagicMock
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
    repo = MagicMock()
    mock_github.return_value.get_repo.return_value = repo
    return repo

def test_list_open_issues(mock_repo):
    issue1 = MagicMock(number=1, title="Test Issue")
    mock_repo.get_issues.return_value = [issue1]
    
    result = list_open_issues("owner/repo")
    
    assert isinstance(result, str)
    assert "#1" in result
    assert "Test Issue" in result

def test_create_issue(mock_repo):
    mock_issue = MagicMock(number=1)
    mock_repo.create_issue.return_value = mock_issue
    
    result = create_issue("owner/repo", "Test Title", "Test Body")
    
    mock_repo.create_issue.assert_called_once_with(
        title="Test Title",
        body="Test Body"
    )
    assert isinstance(result, str)
    assert "#1" in result

def test_read_file(mock_repo):
    mock_content = MagicMock(
        decoded_content=b"test content"
    )
    mock_repo.get_contents.return_value = mock_content
    
    result = read_file("owner/repo", "test.txt")
    
    assert result == "test content"
    mock_repo.get_contents.assert_called_once_with("test.txt")

def test_create_branch(mock_repo):
    mock_ref = MagicMock()
    mock_repo.get_git_ref.return_value.object.sha = "main-sha"
    mock_repo.create_git_ref.return_value = mock_ref
    
    result = create_branch("owner/repo", "test-branch")
    
    mock_repo.create_git_ref.assert_called_once_with(
        ref="refs/heads/test-branch",
        sha="main-sha"
    )
    assert isinstance(result, str)
    assert "test-branch" in result

def test_create_pull_request(mock_repo):
    mock_pr = MagicMock(number=1)
    mock_repo.create_pull.return_value = mock_pr
    
    result = create_pull_request(
        "owner/repo",
        "test-branch",
        "Test PR",
        "Test Description"
    )
    
    mock_repo.create_pull.assert_called_once_with(
        title="Test PR",
        body="Test Description",
        head="test-branch",
        base="main"
    )
    assert isinstance(result, str)
    assert "#1" in result