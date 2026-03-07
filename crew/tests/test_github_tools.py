"""Tests for GitHub tools."""
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
    with patch('src.tools.github_tool.Github') as mock:
        repo = Mock()
        mock.return_value.get_repo.return_value = repo
        yield repo

def test_list_open_issues(mock_github):
    issue1 = Mock(number=1, title='Test Issue 1')
    issue2 = Mock(number=2, title='Test Issue 2')
    mock_github.get_issues.return_value = [issue1, issue2]
    
    issues = list_open_issues('test/repo')
    assert len(issues) == 2
    assert '1: Test Issue 1' in issues
    assert '2: Test Issue 2' in issues
    
    mock_github.get_issues.assert_called_once_with(state='open')

def test_add_labels(mock_github):
    issue = Mock()
    mock_github.get_issue.return_value = issue
    
    add_labels('test/repo', 1, ['bug', 'help wanted'])
    
    mock_github.get_issue.assert_called_once_with(1)
    issue.add_to_labels.assert_called_once_with('bug', 'help wanted')

def test_create_issue(mock_github):
    issue = Mock(number=1)
    mock_github.create_issue.return_value = issue
    
    result = create_issue('test/repo', 'Test Title', 'Test Body')
    assert result == 1
    
    mock_github.create_issue.assert_called_once_with(
        title='Test Title',
        body='Test Body'
    )
