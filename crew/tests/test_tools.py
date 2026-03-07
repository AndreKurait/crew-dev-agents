import pytest
from unittest.mock import Mock, patch
from src.tools.github_tool import list_open_issues, add_labels, create_issue

@pytest.fixture
def mock_github():
    with patch('github.Github') as mock:
        mock_repo = Mock()
        mock.return_value.get_repo.return_value = mock_repo
        yield mock_repo

def test_list_open_issues(mock_github):
    mock_issue1 = Mock()
    mock_issue1.number = 1
    mock_issue1.title = "Test Issue"
    mock_issue1.body = "Issue body"
    mock_issue1.labels = []
    
    mock_github.get_issues.return_value = [mock_issue1]
    
    result = list_open_issues("owner/repo")
    assert isinstance(result, str)
    assert "#1" in result
    assert "Test Issue" in result

def test_add_labels(mock_github):
    mock_issue = Mock()
    mock_github.get_issue.return_value = mock_issue
    
    add_labels("owner/repo", 1, ["bug", "enhancement"])
    
    mock_issue.add_to_labels.assert_called_with("bug", "enhancement")

def test_create_issue(mock_github):
    mock_github.create_issue.return_value = Mock(number=42)
    
    result = create_issue(
        "owner/repo",
        "Test Title",
        "Test Body",
        ["bug"]
    )
    
    mock_github.create_issue.assert_called_once_with(
        title="Test Title",
        body="Test Body",
        labels=["bug"]
    )
    assert "#42" in result