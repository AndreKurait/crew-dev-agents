import json
import os
import sys
import traceback


def create_github_issue(title: str, body: str, labels: list[str] = None):
    """Create a GitHub issue directly."""
    from github import Github, Auth
    import boto3

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        secret_name = os.environ.get("GITHUB_SECRET_NAME", "crew-dev-agents/github-token")
        region = os.environ.get("BEDROCK_REGION", "us-west-2")
        client = boto3.client("secretsmanager", region_name=region)
        resp = client.get_secret_value(SecretId=secret_name)
        token = json.loads(resp["SecretString"])["GITHUB_TOKEN"]

    gh = Github(auth=Auth.Token(token))
    repo_url = os.environ.get("REPO_URL", "")
    repo_name = repo_url.rstrip("/").split("github.com/")[-1].removesuffix(".git")
    repo = gh.get_repo(repo_name)
    issue = repo.create_issue(title=title, body=body, labels=labels or [])
    print(f"Created issue #{issue.number}: {issue.html_url}")
    return issue


def main():
    repo_url = os.environ.get("REPO_URL")
    if not repo_url:
        print("ERROR: REPO_URL required", file=sys.stderr)
        sys.exit(1)

    print(f"Starting crew for {repo_url}")

    try:
        from src.crew import build_crew
        crew = build_crew(repo_url)
        result = crew.kickoff()
        output = str(result)
        print(f"Crew completed. Output length: {len(output)}")

        # Evaluate
        score = 0.0
        if output and len(output) > 100:
            score += 0.3
        if "number" in output:
            score += 0.4
        if "error" not in output.lower():
            score += 0.3
        print(f"Quality score: {score:.2f}")

    except Exception as e:
        output = ""
        score = 0.1
        print(f"Crew failed: {e}")
        traceback.print_exc()

    # Always create a self-improvement issue when score is low
    if score < 0.5:
        print("Score below threshold, creating self-improvement issue...")
        try:
            create_github_issue(
                title=f"[Auto] Self-improvement needed (score: {score:.2f})",
                body=(
                    f"## Automated Self-Evaluation Report\n\n"
                    f"**Quality Score**: {score:.2f}\n"
                    f"**Output Length**: {len(output)}\n\n"
                    f"### Suggested Improvements\n"
                    f"- [ ] Add unit tests (pytest) for crew tools\n"
                    f"- [ ] Add ruff linting configuration\n"
                    f"- [ ] Add pre-commit hooks\n"
                    f"- [ ] Improve error handling in tools\n"
                    f"- [ ] Add type hints throughout codebase\n"
                    f"- [ ] Add comprehensive README for crew/ directory\n"
                    f"- [ ] Add GitHub Actions workflow for linting and tests\n"
                    f"- [ ] Fix Bedrock Converse API tool calling compatibility\n"
                ),
                labels=["self-improvement", "automated"],
            )
        except Exception as e:
            print(f"Failed to create issue: {e}")
            traceback.print_exc()


if __name__ == "__main__":
    main()
