import json
import os
import uuid

from crewai.tools import tool
from github import Github, Auth, GithubException


def _get_github() -> Github:
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
    """List open issues from the target repo. Returns JSON array."""
    try:
        gh = _get_github()
        repo = gh.get_repo(_repo_name())
        issues = []
        for issue in repo.get_issues(state="open", sort="created", direction="desc"):
            if len(issues) >= limit:
                break
            if issue.pull_request:
                continue
            issues.append({"number": issue.number, "title": issue.title, "body": (issue.body or "")[:500], "labels": [l.name for l in issue.labels]})
        return json.dumps(issues) if issues else "No open issues found."
    except Exception as e:
        return f"Error: {e}"


@tool("list_open_prs")
def list_open_prs(limit: int = 10) -> str:
    """List open PRs awaiting review. Returns JSON array."""
    try:
        gh = _get_github()
        repo = gh.get_repo(_repo_name())
        prs = []
        for pr in repo.get_pulls(state="open", sort="created", direction="desc"):
            if len(prs) >= limit:
                break
            prs.append({"number": pr.number, "title": pr.title, "body": (pr.body or "")[:500], "user": pr.user.login})
        return json.dumps(prs) if prs else "No open PRs found."
    except Exception as e:
        return f"Error: {e}"


@tool("add_issue_comment")
def add_issue_comment(issue_number: int, comment: str) -> str:
    """Add a comment to a GitHub issue."""
    try:
        gh = _get_github()
        repo = gh.get_repo(_repo_name())
        c = repo.get_issue(int(issue_number)).create_comment(comment)
        return json.dumps({"comment_id": c.id, "url": c.html_url})
    except Exception as e:
        return f"Error: {e}"


@tool("add_labels")
def add_labels(issue_number: int, labels: str) -> str:
    """Add labels to a GitHub issue. Labels is a comma-separated string."""
    try:
        gh = _get_github()
        repo = gh.get_repo(_repo_name())
        label_list = [l.strip() for l in labels.split(",")]
        repo.get_issue(int(issue_number)).add_to_labels(*label_list)
        return json.dumps({"added": label_list})
    except Exception as e:
        return f"Error: {e}"


@tool("create_issue")
def create_issue(title: str, body: str, labels: str = "") -> str:
    """Create a new GitHub issue. Returns JSON with issue number and URL."""
    try:
        gh = _get_github()
        repo = gh.get_repo(_repo_name())
        label_list = [l.strip() for l in labels.split(",") if l.strip()] if labels else []
        issue = repo.create_issue(title=title, body=body, labels=label_list)
        return json.dumps({"number": issue.number, "url": issue.html_url})
    except Exception as e:
        return f"Error: {e}"


@tool("get_repo_contents")
def get_repo_contents(path: str = "") -> str:
    """List files and directories at a path in the repo."""
    try:
        gh = _get_github()
        repo = gh.get_repo(_repo_name())
        contents = repo.get_contents(path)
        if not isinstance(contents, list):
            contents = [contents]
        return json.dumps([{"name": c.name, "type": c.type, "path": c.path} for c in contents])
    except Exception as e:
        return f"Error: {e}"


@tool("read_file")
def read_file(path: str) -> str:
    """Read a file from the repo. Returns content (max 5000 chars)."""
    try:
        gh = _get_github()
        repo = gh.get_repo(_repo_name())
        content = repo.get_contents(path)
        return content.decoded_content.decode("utf-8")[:5000]
    except Exception as e:
        return f"Error: {e}"


@tool("create_or_update_file")
def create_or_update_file(path: str, content: str, message: str, branch: str = "main") -> str:
    """Create or update a file in the repo on the given branch. Returns JSON with commit SHA."""
    try:
        gh = _get_github()
        repo = gh.get_repo(_repo_name())
        try:
            existing = repo.get_contents(path, ref=branch)
            result = repo.update_file(path, message, content, existing.sha, branch=branch)
            return json.dumps({"action": "updated", "sha": result["commit"].sha})
        except GithubException:
            result = repo.create_file(path, message, content, branch=branch)
            return json.dumps({"action": "created", "sha": result["commit"].sha})
    except Exception as e:
        return f"Error: {e}"


@tool("create_branch")
def create_branch(branch_name: str) -> str:
    """Create a new branch from main. Returns JSON with branch ref."""
    try:
        gh = _get_github()
        repo = gh.get_repo(_repo_name())
        main_ref = repo.get_git_ref("heads/main")
        repo.create_git_ref(f"refs/heads/{branch_name}", main_ref.object.sha)
        return json.dumps({"branch": branch_name, "sha": main_ref.object.sha})
    except Exception as e:
        return f"Error: {e}"


@tool("create_pull_request")
def create_pull_request(title: str, body: str, head_branch: str, base_branch: str = "main") -> str:
    """Create a pull request. Returns JSON with PR number and URL."""
    try:
        gh = _get_github()
        repo = gh.get_repo(_repo_name())
        pr = repo.create_pull(title=title, body=body, head=head_branch, base=base_branch)
        return json.dumps({"number": pr.number, "url": pr.html_url})
    except Exception as e:
        return f"Error: {e}"


@tool("merge_pull_request")
def merge_pull_request(pr_number: int) -> str:
    """Merge a pull request by number. Returns JSON with merge status."""
    try:
        gh = _get_github()
        repo = gh.get_repo(_repo_name())
        pr = repo.get_pull(int(pr_number))
        result = pr.merge(merge_method="squash")
        return json.dumps({"merged": result.merged, "sha": result.sha})
    except Exception as e:
        return f"Error: {e}"


@tool("close_issue")
def close_issue(issue_number: int, comment: str = "") -> str:
    """Close a GitHub issue, optionally with a comment."""
    try:
        gh = _get_github()
        repo = gh.get_repo(_repo_name())
        issue = repo.get_issue(int(issue_number))
        if comment:
            issue.create_comment(comment)
        issue.edit(state="closed")
        return json.dumps({"closed": issue_number})
    except Exception as e:
        return f"Error: {e}"
