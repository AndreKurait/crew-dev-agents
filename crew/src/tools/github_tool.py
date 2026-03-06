import json
import os

from crewai.tools import tool
from github import Github, Auth


def _get_github() -> Github:
    """Get authenticated GitHub client."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        import boto3
        secret_name = os.environ.get("GITHUB_SECRET_NAME", "crew-dev-agents/github-token")
        region = os.environ.get("BEDROCK_REGION", "us-west-2")
        client = boto3.client("secretsmanager", region_name=region)
        resp = client.get_secret_value(SecretId=secret_name)
        token = json.loads(resp["SecretString"])["GITHUB_TOKEN"]
    return Github(auth=Auth.Token(token))


def _repo_name() -> str:
    url = os.environ.get("REPO_URL", "")
    return url.rstrip("/").split("github.com/")[-1].removesuffix(".git")


@tool("list_open_issues")
def list_open_issues(limit: int = 20) -> str:
    """List open issues from the target repo that need triage (no labels). Returns JSON."""
    gh = _get_github()
    repo = gh.get_repo(_repo_name())
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
    return json.dumps(issues) if issues else "No open issues found."


@tool("list_open_prs")
def list_open_prs(limit: int = 10) -> str:
    """List open PRs awaiting review. Returns JSON."""
    gh = _get_github()
    repo = gh.get_repo(_repo_name())
    prs = []
    for pr in repo.get_pulls(state="open", sort="created", direction="desc")[:limit]:
        prs.append({
            "number": pr.number,
            "title": pr.title,
            "body": (pr.body or "")[:500],
            "user": pr.user.login,
        })
    return json.dumps(prs) if prs else "No open PRs found."


@tool("add_issue_comment")
def add_issue_comment(issue_number: int, comment: str) -> str:
    """Add a comment to a GitHub issue."""
    gh = _get_github()
    repo = gh.get_repo(_repo_name())
    issue = repo.get_issue(int(issue_number))
    c = issue.create_comment(comment)
    return json.dumps({"comment_id": c.id, "url": c.html_url})


@tool("add_labels")
def add_labels(issue_number: int, labels: str) -> str:
    """Add labels to a GitHub issue. Labels is a comma-separated string."""
    gh = _get_github()
    repo = gh.get_repo(_repo_name())
    issue = repo.get_issue(int(issue_number))
    label_list = [l.strip() for l in labels.split(",")]
    issue.add_to_labels(*label_list)
    return json.dumps({"added": label_list})


@tool("create_issue")
def create_issue(title: str, body: str, labels: str = "") -> str:
    """Create a new GitHub issue. Labels is optional comma-separated string."""
    gh = _get_github()
    repo = gh.get_repo(_repo_name())
    label_list = [l.strip() for l in labels.split(",") if l.strip()] if labels else []
    issue = repo.create_issue(title=title, body=body, labels=label_list)
    return json.dumps({"number": issue.number, "url": issue.html_url})


@tool("get_repo_contents")
def get_repo_contents(path: str = "") -> str:
    """List files/dirs at a path in the repo. Empty path = root."""
    gh = _get_github()
    repo = gh.get_repo(_repo_name())
    contents = repo.get_contents(path)
    if not isinstance(contents, list):
        contents = [contents]
    return json.dumps([{"name": c.name, "type": c.type, "path": c.path} for c in contents])


@tool("read_file")
def read_file(path: str) -> str:
    """Read a file from the repo. Returns the file content."""
    gh = _get_github()
    repo = gh.get_repo(_repo_name())
    content = repo.get_contents(path)
    return content.decoded_content.decode("utf-8")[:5000]
