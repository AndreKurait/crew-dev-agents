"""Test cases for GitHub tools."""
import pytest
from unittest.mock import Mock, patch
from src.tools.github_tool import (
    list_open_issues,
    list_open_prs,
    add_issue_comment,
    add_labels,
    create_issue,
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
    """Test listing open issues."""
    # Arrange
    mock_issue = Mock()
    mock_issue.number = 1
    mock_issue.title = 'Test Issue'
    mock_issue.body = 'Test Body'
    mock_issue.labels = ['bug']
    mock_repo.get_issues.return_value = [mock_issue]

    # Act
    result = list_open_issues('owner/repo')

    # Assert
    assert len(result) == 1
    assert result[0]['number'] == 1
    assert result[0]['title'] == 'Test Issue'

def test_create_issue(mock_repo):
    """Test creating an issue."""
    # Arrange
    mock_issue = Mock()
    mock_issue.number = 2
    mock_repo.create_issue.return_value = mock_issue

    # Act
    result = create_issue('owner/repo', 'New Issue', 'Issue Body')

    # Assert
    mock_repo.create_issue.assert_called_once_with(
        title='New Issue',
        body='Issue Body'
    )
    assert result == 2

def test_add_labels(mock_repo):
    """Test adding labels to an issue."""
    # Arrange
    mock_issue = Mock()
    mock_repo.get_issue.return_value = mock_issue

    # Act
    add_labels('owner/repo', 1, ['bug', 'help wanted'])

    # Assert
    mock_repo.get_issue.assert_called_once_with(1)
    mock_issue.add_to_labels.assert_called_once_with('bug', 'help wanted')

def test_add_issue_comment(mock_repo):
    """Test adding a comment to an issue."""
    # Arrange
    mock_issue = Mock()
    mock_repo.get_issue.return_value = mock_issue

    # Act
    add_issue_comment('owner/repo', 1, 'Test comment')

    # Assert
    mock_repo.get_issue.assert_called_once_with(1)
    mock_issue.create_comment.assert_called_once_with('Test comment')
