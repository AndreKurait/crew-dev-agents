import os
from unittest import mock

import pytest
from github import Github, Repository
from github.Issue import Issue

from src.tools.github_tool import (
    list_open_issues,
    add_labels,
    create_issue,
    get_repo_contents,
    read_file,
)


@pytest.fixture
def mock_repo():
    repo = mock.Mock(spec=Repository.Repository)
    repo.get_issues.return_value = []
    return repo


@pytest.fixture
def mock_github(mock_repo):
    github = mock.Mock(spec=Github)
    github.get_repo.return_value = mock_repo
    return github


def test_list_open_issues(mock_github, mock_repo):
    with mock.patch('src.tools.github_tool.Github', return_value=mock_github):
        mock_issue = mock.Mock(spec=Issue)
        mock_issue.number = 1
        mock_issue.title = "Test Issue"
        mock_issue.labels = []
        mock_repo.get_issues.return_value = [mock_issue]

        issues = list_open_issues("owner/repo")
        assert len(issues) == 1
        assert issues[0]["number"] == 1
        assert issues[0]["title"] == "Test Issue"


def test_add_labels(mock_github, mock_repo):
    with mock.patch('src.tools.github_tool.Github', return_value=mock_github):
        mock_issue = mock.Mock(spec=Issue)
        mock_repo.get_issue.return_value = mock_issue

        add_labels("owner/repo", 1, ["bug", "enhancement"])
        mock_issue.add_to_labels.assert_called_once_with("bug", "enhancement")


def test_create_issue(mock_github, mock_repo):
    with mock.patch('src.tools.github_tool.Github', return_value=mock_github):
        mock_repo.create_issue.return_value.number = 42

        issue_num = create_issue(
            "owner/repo",
            "Test Issue",
            "Description",
            labels=["bug"]
        )
        assert issue_num == 42
        mock_repo.create_issue.assert_called_once_with(
            title="Test Issue",
            body="Description",
            labels=["bug"]
        )


def test_get_repo_contents(mock_github, mock_repo):
    with mock.patch('src.tools.github_tool.Github', return_value=mock_github):
        mock_content = mock.Mock()
        mock_content.path = "test.py"
        mock_content.type = "file"
        mock_repo.get_contents.return_value = [mock_content]

        contents = get_repo_contents("owner/repo", "")
        assert len(contents) == 1
        assert contents[0]["path"] == "test.py"
        assert contents[0]["type"] == "file"


def test_read_file(mock_github, mock_repo):
    with mock.patch('src.tools.github_tool.Github', return_value=mock_github):
        mock_content = mock.Mock()
        mock_content.decoded_content.decode.return_value = "file content"
        mock_repo.get_contents.return_value = mock_content

        content = read_file("owner/repo", "test.py")
        assert content == "file content"
