from unittest.mock import Mock, patch
import pytest
from src.tools.github_tool import (
    list_open_issues,
    add_labels,
    create_issue,
    read_file
)

@pytest.fixture
def mock_github():
    with patch('src.tools.github_tool.Github') as mock:
        mock_repo = Mock()
        mock.return_value.get_repo.return_value = mock_repo
        yield mock_repo

def test_list_open_issues(mock_github):
    mock_issue = Mock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.labels = []
    mock_github.get_issues.return_value = [mock_issue]
    
    result = list_open_issues("owner/repo")
    assert len(result) == 1
    assert result[0]['number'] == 1
    assert result[0]['title'] == "Test Issue"

def test_add_labels(mock_github):
    mock_issue = Mock()
    mock_github.get_issue.return_value = mock_issue
    
    add_labels("owner/repo", 1, ["bug", "help wanted"])
    mock_issue.add_to_labels.assert_called_with("bug", "help wanted")

def test_create_issue(mock_github):
    mock_issue = Mock()
    mock_issue.number = 2
    mock_github.create_issue.return_value = mock_issue
    
    result = create_issue(
        "owner/repo",
        "Test Issue",
        "Test Description",
        ["enhancement"]
    )
    assert result == 2
    mock_github.create_issue.assert_called_once()

def test_read_file(mock_github):
    mock_content = Mock()
    mock_content.decoded_content.decode.return_value = "file content"
    mock_github.get_contents.return_value = mock_content
    
    result = read_file("owner/repo", "path/to/file")
    assert result == "file content"
    mock_github.get_contents.assert_called_with("path/to/file")