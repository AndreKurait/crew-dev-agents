"""
Agent-as-planner pattern: LLM decides what to do, Python executes it.
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


def list_all_files(repo, path="", depth=0):
    """Recursively list all files up to depth 3."""
    files = []
    if depth > 3:
        return files
    try:
        for item in repo.get_contents(path):
            files.append({"path": item.path, "type": item.type})
            if item.type == "dir" and depth < 3:
                files.extend(list_all_files(repo, item.path, depth + 1))
    except Exception:
        pass
    return files


def gather_context():
    """Read repo structure, key files, recent PRs, and issues."""
    repo = get_repo()
    ctx = {}

    # Full file tree
    ctx["all_files"] = list_all_files(repo)

    # Read key files
    key_files = [
        "README.md", "crew/pyproject.toml", "crew/Dockerfile",
        "crew/src/main.py", "crew/src/crew.py",
        "crew/config/agents.yaml", "crew/config/tasks.yaml",
        "crew/src/tools/github_tool.py", "crew/src/tools/metrics_tool.py",
    ]
    ctx["file_contents"] = {}
    for path in key_files:
        try:
            content = repo.get_contents(path)
            ctx["file_contents"][path] = content.decoded_content.decode("utf-8")[:2000]
        except Exception:
            pass

    # Open issues
    ctx["open_issues"] = []
    for issue in repo.get_issues(state="open", sort="created", direction="desc"):
        if issue.pull_request:
            continue
        ctx["open_issues"].append({"number": issue.number, "title": issue.title})
        if len(ctx["open_issues"]) >= 10:
            break

    # Recent merged PRs (to avoid duplicating work)
    ctx["recent_prs"] = []
    for pr in repo.get_pulls(state="closed", sort="updated", direction="desc"):
        if pr.merged and len(ctx["recent_prs"]) < 15:
            ctx["recent_prs"].append({"number": pr.number, "title": pr.title})

    return ctx


def ask_llm_for_plan(context: dict) -> dict:
    """Ask the LLM to produce a structured improvement plan."""
    from crewai import LLM

    model = os.environ.get("BEDROCK_MODEL", "bedrock/anthropic.claude-3-5-sonnet-20241022-v2:0")
    llm = LLM(model=model)

    all_file_paths = [f["path"] for f in context["all_files"]]
    recent_pr_titles = [pr["title"] for pr in context["recent_prs"]]

    prompt = f"""You are a developer agent that improves a GitHub repository.

REPO FILE TREE:
{json.dumps(all_file_paths, indent=2)}

RECENT MERGED PRs (DO NOT duplicate these — pick something DIFFERENT):
{json.dumps(recent_pr_titles, indent=2)}

OPEN ISSUES:
{json.dumps(context['open_issues'], indent=2)}

KEY FILE CONTENTS:
{json.dumps(context['file_contents'], indent=2)}

RULES:
- Pick ONE improvement that has NOT been done in recent PRs
- Do NOT add more GitHub tool tests (already done many times)
- Do NOT add ruff config (already done)
- Focus on something NEW. Good options:
  * Add a GitHub Actions workflow for running pytest and ruff
  * Add crew/README.md documenting how the crew works
  * Add tests for metrics_tool.py or self_eval_flow.py
  * Add type hints to a file that's missing them
  * Add a pre-commit config
  * Improve the Dockerfile (multi-stage build, non-root user)
  * Add __init__.py files where missing
  * Fix any actual bugs you see in the code

Respond with ONLY valid JSON (no markdown, no code fences):
{{
  "improvement": "short description of what you're doing",
  "branch_name": "auto/descriptive-name",
  "files": [
    {{
      "path": "path/to/file",
      "content": "THE COMPLETE FILE CONTENT",
      "message": "commit message for this file"
    }}
  ],
  "pr_title": "Clear PR title",
  "pr_body": "Description of what this PR does and why",
  "close_issues": []
}}"""

    response = llm.call([{"role": "user", "content": prompt}])
    text = str(response)
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    raise ValueError(f"No JSON found in LLM response: {text[:500]}")


def execute_plan(plan: dict):
    """Execute: create branch, write files, create PR, merge."""
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
        print(f"  Writing: {path}")
        try:
            existing = repo.get_contents(path, ref=branch)
            repo.update_file(path, message, content, existing.sha, branch=branch)
        except GithubException:
            repo.create_file(path, message, content, branch=branch)

    print(f"Creating PR: {plan['pr_title']}")
    pr = repo.create_pull(title=plan["pr_title"], body=plan["pr_body"], head=branch, base="main")
    print(f"  PR #{pr.number}: {pr.html_url}")

    print(f"Merging PR #{pr.number}")
    pr.merge(merge_method="squash")

    for issue_num in plan.get("close_issues", []):
        try:
            issue = repo.get_issue(int(issue_num))
            issue.create_comment(f"Fixed by #{pr.number}")
            issue.edit(state="closed")
            print(f"  Closed issue #{issue_num}")
        except Exception:
            pass

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
        print(f"  {len(context['all_files'])} files, {len(context['open_issues'])} issues, {len(context['recent_prs'])} recent PRs")

        print("Asking LLM for improvement plan...")
        plan = ask_llm_for_plan(context)
        print(f"  Plan: {plan['improvement']}")
        print(f"  Files: {[f['path'] for f in plan['files']]}")

        print("Executing plan...")
        pr_num = execute_plan(plan)
        print(f"=== SUCCESS: PR #{pr_num} merged ===")

    except Exception as e:
        print(f"=== FAILED: {e} ===")
        traceback.print_exc()


if __name__ == "__main__":
    main()
