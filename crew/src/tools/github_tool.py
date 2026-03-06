import json
import os

from crewai.tools import tool
from github import Github, Auth


def _get_github() -> Github:
    """Get authenticated GitHub client. Reads token from env or Secrets Manager."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        import boto3
        secret_name = os.environ.get("GITHUB_SECRET_NAME", "crew-dev-agents/github-token")
        region = os.environ.get("BEDROCK_REGION", "us-west-2")
        client = boto3.client("secretsmanager", region_name=region)
        resp = client.get_secret_value(SecretId=secret_name)
        token = json.loads(resp["SecretString"])["GITHUB_TOKEN"]
    return Github(auth=Auth.Token(token))


@tool("list_open_issues")
def list_open_issues(repo_url: str, limit: int = 20) -> str:
    """List open issues from a GitHub repo that need triage (no labels)."""
    gh = _get_github()
    repo_name = repo_url.rstrip("/").split("github.com/")[-1].removesuffix(".git")
    repo = gh.get_repo(repo_name)
    issues = []
    for issue in repo.get_issues(state="open", sort="created", direction="desc")[:limit]:
        if issue.pull_request:
            continue
        issues.append({
            "number": issue.number,
            "title": issue.title,
            "body": (issue.body or "")[:500],
            "labels": [l.name for l in issue.labels],
            "assignees": [a.login for a in issue.assignees],
        })
    return json.dumps(issues)


@tool("list_open_prs")
def list_open_prs(repo_url: str, limit: int = 10) -> str:
    """List open PRs awaiting review."""
    gh = _get_github()
    repo_name = repo_url.rstrip("/").split("github.com/")[-1].removesuffix(".git")
    repo = gh.get_repo(repo_name)
    prs = []
    for pr in repo.get_pulls(state="open", sort="created", direction="desc")[:limit]:
        prs.append({
            "number": pr.number,
            "title": pr.title,
            "body": (pr.body or "")[:500],
            "diff_url": pr.diff_url,
            "user": pr.user.login,
        })
    return json.dumps(prs)


@tool("add_issue_comment")
def add_issue_comment(repo_url: str, issue_number: int, comment: str) -> str:
    """Add a comment to a GitHub issue."""
    gh = _get_github()
    repo_name = repo_url.rstrip("/").split("github.com/")[-1].removesuffix(".git")
    repo = gh.get_repo(repo_name)
    issue = repo.get_issue(int(issue_number))
    c = issue.create_comment(comment)
    return json.dumps({"comment_id": c.id, "url": c.html_url})


@tool("add_labels")
def add_labels(repo_url: str, issue_number: int, labels: str) -> str:
    """Add labels to a GitHub issue. Labels is a comma-separated string."""
    gh = _get_github()
    repo_name = repo_url.rstrip("/").split("github.com/")[-1].removesuffix(".git")
    repo = gh.get_repo(repo_name)
    issue = repo.get_issue(int(issue_number))
    label_list = [l.strip() for l in labels.split(",")]
    issue.add_to_labels(*label_list)
    return json.dumps({"added": label_list})
