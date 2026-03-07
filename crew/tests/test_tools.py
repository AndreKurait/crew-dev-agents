import pytest
from unittest.mock import MagicMock, patch

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
        mock_repo = MagicMock()
        mock.return_value.get_repo.return_value = mock_repo
        yield mock, mock_repo

def test_list_open_issues(mock_github):
    _, mock_repo = mock_github
    mock_issue = MagicMock()
    mock_issue.number = 1
    mock_issue.title = "Test Issue"
    mock_issue.body = "Issue body"
    mock_repo.get_issues.return_value = [mock_issue]

    result = list_open_issues()
    assert len(result) == 1
    assert result[0]['number'] == 1
    assert result[0]['title'] == "Test Issue"

def test_create_issue(mock_github):
    _, mock_repo = mock_github
    mock_issue = MagicMock()
    mock_issue.number = 2
    mock_repo.create_issue.return_value = mock_issue

    result = create_issue("New Issue", "Issue Description")
    assert result == 2
    mock_repo.create_issue.assert_called_once_with(
        title="New Issue",
        body="Issue Description"
    )

def test_create_branch(mock_github):
    _, mock_repo = mock_github
    mock_ref = MagicMock()
    mock_repo.get_git_ref.return_value.object.sha = "main-sha"
    mock_repo.create_git_ref.return_value = mock_ref

    result = create_branch("feature/test")
    assert result is True
    mock_repo.create_git_ref.assert_called_once_with(
        ref="refs/heads/feature/test",
        sha="main-sha"
    )

def test_create_pull_request(mock_github):
    _, mock_repo = mock_github
    mock_pr = MagicMock()
    mock_pr.number = 3
    mock_repo.create_pull.return_value = mock_pr

    result = create_pull_request(
        "feature/test",
        "main",
        "Test PR",
        "PR Description",
        [1]
    )
    assert result == 3
    mock_repo.create_pull.assert_called_once_with(
        title="Test PR",
        body="PR Description\n\nCloses #1",
        head="feature/test",
        base="main"
    )
