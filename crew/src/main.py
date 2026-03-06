"""
Agent-as-planner pattern: LLM decides what to do, Python executes it.
Bypasses CrewAI/Bedrock tool calling bug entirely.
"""
import json
import os
import sys
import traceback
import uuid

from github import Github, Auth, GithubException


def get_github():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        import boto3
        secret_name = os.environ.get("GITHUB_SECRET_NAME", "crew-dev-agents/github-token")
        region = os.environ.get("BEDROCK_REGION", "us-west-2")
        client = boto3.client("secretsmanager", region_name=region)
        resp = client.get_secret_value(SecretId=secret_name)
        token = json.loads(resp["SecretString"])["GITHUB_TOKEN"]
    return Github(auth=Auth.Token(token))


def get_repo():
    url = os.environ.get("REPO_URL", "")
    name = url.rstrip("/").split("github.com/")[-1].removesuffix(".git")
    return get_github().get_repo(name)


def gather_context():
    """Read repo structure and key files to give the LLM context."""
    repo = get_repo()
    ctx = {"files": [], "issues": [], "prs": []}

    # Repo structure
    for item in repo.get_contents(""):
        ctx["files"].append({"path": item.path, "type": item.type})
    for item in repo.get_contents("crew/src"):
        ctx["files"].append({"path": item.path, "type": item.type})

    # Read key files
    key_files = ["README.md", "crew/pyproject.toml", "crew/src/crew.py", "crew/config/agents.yaml", "crew/config/tasks.yaml"]
    ctx["file_contents"] = {}
    for path in key_files:
        try:
            content = repo.get_contents(path)
            ctx["file_contents"][path] = content.decoded_content.decode("utf-8")[:3000]
        except Exception:
            pass

    # Open issues
    for issue in repo.get_issues(state="open", sort="created", direction="desc"):
        if issue.pull_request:
            continue
        ctx["issues"].append({"number": issue.number, "title": issue.title, "labels": [l.name for l in issue.labels]})
        if len(ctx["issues"]) >= 10:
            break

    # Open PRs
    for pr in repo.get_pulls(state="open"):
        ctx["prs"].append({"number": pr.number, "title": pr.title})
        if len(ctx["prs"]) >= 5:
            break

    return ctx


def ask_llm_for_plan(context: dict) -> dict:
    """Ask the LLM to produce a structured improvement plan."""
    from crewai import LLM

    model = os.environ.get("BEDROCK_MODEL", "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0")
    llm = LLM(model=model)

    prompt = f"""You are a developer agent maintaining a GitHub repository.

Here is the current state of the repo:

FILES: {json.dumps(context['files'])}

OPEN ISSUES: {json.dumps(context['issues'])}

KEY FILE CONTENTS:
{json.dumps(context['file_contents'], indent=2)}

Your job: Pick ONE concrete improvement to make. Choose from:
1. Add a pytest test file (crew/tests/test_tools.py)
2. Add ruff linting config to pyproject.toml
3. Add a crew/README.md with documentation
4. Fix a bug you see in the code
5. Improve an agent or task definition

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "improvement": "short description",
  "branch_name": "auto/short-name",
  "files": [
    {{
      "path": "path/to/file",
      "content": "full file content here",
      "message": "commit message"
    }}
  ],
  "pr_title": "PR title",
  "pr_body": "PR description",
  "close_issues": [list of issue numbers to close, or empty]
}}"""

    response = llm.call([{"role": "user", "content": prompt}])
    # Extract JSON from response
    text = str(response)
    # Find JSON in response
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    raise ValueError(f"No JSON found in LLM response: {text[:200]}")


def execute_plan(plan: dict):
    """Execute the improvement plan: create branch, write files, create PR, merge."""
    repo = get_repo()
    branch = plan["branch_name"]

    print(f"Creating branch: {branch}")
    main_ref = repo.get_git_ref("heads/main")
    try:
        repo.create_git_ref(f"refs/heads/{branch}", main_ref.object.sha)
    except GithubException as e:
        if "Reference already exists" in str(e):
            branch = f"{branch}-{uuid.uuid4().hex[:6]}"
            repo.create_git_ref(f"refs/heads/{branch}", main_ref.object.sha)
        else:
            raise

    for file_spec in plan["files"]:
        path = file_spec["path"]
        content = file_spec["content"]
        message = file_spec.get("message", f"Update {path}")
        print(f"Writing: {path}")
        try:
            existing = repo.get_contents(path, ref=branch)
            repo.update_file(path, message, content, existing.sha, branch=branch)
        except GithubException:
            repo.create_file(path, message, content, branch=branch)

    print(f"Creating PR: {plan['pr_title']}")
    pr = repo.create_pull(
        title=plan["pr_title"],
        body=plan["pr_body"],
        head=branch,
        base="main",
    )
    print(f"PR #{pr.number}: {pr.html_url}")

    print(f"Merging PR #{pr.number}")
    pr.merge(merge_method="squash")

    for issue_num in plan.get("close_issues", []):
        try:
            issue = repo.get_issue(int(issue_num))
            issue.create_comment(f"Fixed by #{pr.number}")
            issue.edit(state="closed")
            print(f"Closed issue #{issue_num}")
        except Exception as e:
            print(f"Failed to close issue #{issue_num}: {e}")

    return pr.number


def main():
    repo_url = os.environ.get("REPO_URL")
    if not repo_url:
        print("ERROR: REPO_URL required", file=sys.stderr)
        sys.exit(1)

    print(f"=== Crew Dev Agents: Self-Improvement Run ===")
    print(f"Repo: {repo_url}")

    try:
        print("Gathering repo context...")
        context = gather_context()
        print(f"Found {len(context['files'])} files, {len(context['issues'])} issues, {len(context['prs'])} PRs")

        print("Asking LLM for improvement plan...")
        plan = ask_llm_for_plan(context)
        print(f"Plan: {plan['improvement']}")
        print(f"Files to change: {[f['path'] for f in plan['files']]}")

        print("Executing plan...")
        pr_num = execute_plan(plan)
        print(f"=== SUCCESS: PR #{pr_num} merged ===")

    except Exception as e:
        print(f"=== FAILED: {e} ===")
        traceback.print_exc()
        # Create self-improvement issue
        try:
            repo = get_repo()
            repo.create_issue(
                title=f"[Auto] Self-improvement failed: {type(e).__name__}",
                body=f"## Error\n```\n{e}\n```\n\n## Traceback\n```\n{traceback.format_exc()[:2000]}\n```",
                labels=["self-improvement", "automated"],
            )
            print("Created failure issue")
        except Exception:
            pass


if __name__ == "__main__":
    main()
