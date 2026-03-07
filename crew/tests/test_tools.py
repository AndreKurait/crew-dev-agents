from unittest.mock import patch, MagicMock
import pytest
from src.tools.github_tool import list_open_issues, add_labels, create_issue

@pytest.fixture
def mock_github():
    with patch('src.tools.github_tool.Github') as mock:
        mock_repo = MagicMock()
        mock.return_value.get_repo.return_value = mock_repo
        yield mock_repo

def test_list_open_issues(mock_github):
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.labels = []
    mock_github.get_issues.return_value = [mock_issue]

    issues = list_open_issues("owner/repo")
    assert len(issues) == 1
    assert issues[0]["number"] == 1
    assert issues[0]["title"] == "Test Issue"

def test_add_labels(mock_github):
    mock_issue = MagicMock()
    mock_github.get_issue.return_value = mock_issue

    add_labels("owner/repo", 1, ["bug", "enhancement"])
    mock_issue.add_to_labels.assert_called_with("bug", "enhancement")

def test_create_issue(mock_github):
    mock_issue = MagicMock()
    mock_issue.number = 2
    mock_github.create_issue.return_value = mock_issue

    result = create_issue(
        "owner/repo",
        "Test Issue",
        "Issue Description",
        labels=["test"]
    )
    assert result == 2
    mock_github.create_issue.assert_called_once_with(
        title="Test Issue",
        body="Issue Description",
        labels=["test"]
    )
