import json
import os

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

from src.crew import build_crew


class FlowState(BaseModel):
    repo_url: str = ""
    retry_count: int = 0
    max_retries: int = 1
    quality_score: float = 0.0
    quality_threshold: float = 0.5
    crew_output: str = ""
    error: str = ""


class SelfEvalFlow(Flow[FlowState]):

    @start()
    def run_crew(self):
        self.state.repo_url = os.environ.get("REPO_URL", self.state.repo_url)
        try:
            crew = build_crew(self.state.repo_url)
            result = crew.kickoff()
            self.state.crew_output = str(result)
        except Exception as e:
            self.state.error = f"{type(e).__name__}: {e}"
            self.state.crew_output = ""
            print(f"Crew error (will still evaluate): {self.state.error}")

    @router(run_crew)
    def evaluate(self):
        output = self.state.crew_output
        if self.state.error:
            score = 0.1
        else:
            score = 0.0
            if output and len(output) > 100:
                score += 0.3
            if "issue_number" in output or "pr_number" in output or "number" in output:
                score += 0.4
            if "error" not in output.lower():
                score += 0.3
        self.state.quality_score = score
        if score >= self.state.quality_threshold:
            return "finalize"
        if self.state.retry_count < self.state.max_retries:
            self.state.retry_count += 1
            return "retry"
        return "finalize"

    @listen("retry")
    def retry_crew(self):
        self.state.error = ""
        self.run_crew()

    @listen("finalize")
    def finalize(self):
        print(f"Flow complete. Score: {self.state.quality_score:.2f}, Error: {self.state.error or 'none'}")
        # Always create a self-improvement issue when score is low
        if self.state.quality_score < self.state.quality_threshold:
            _create_improvement_issue(self.state)


def _create_improvement_issue(state):
    """Create a GitHub issue directly (not through CrewAI tool)."""
    try:
        from github import Github, Auth
        import boto3

        # Get token
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

        issue = repo.create_issue(
            title=f"[Auto] Self-improvement needed: score {state.quality_score:.2f}",
            body=(
                f"## Automated Self-Evaluation Report\n\n"
                f"**Quality Score**: {state.quality_score:.2f} / {state.quality_threshold}\n"
                f"**Retries**: {state.retry_count}\n"
                f"**Error**: `{state.error or 'none'}`\n\n"
                f"### What Happened\n"
                f"The crew ran but scored below the quality threshold. "
                f"The agents were unable to successfully use tools to create issues.\n\n"
                f"### Suggested Improvements\n"
                f"- [ ] Add unit tests for all crew tools (pytest)\n"
                f"- [ ] Add ruff linting configuration\n"
                f"- [ ] Add pre-commit hooks\n"
                f"- [ ] Improve error handling in tools\n"
                f"- [ ] Add type hints throughout codebase\n"
                f"- [ ] Add comprehensive README for crew/ directory\n"
                f"- [ ] Add GitHub Actions for linting and tests\n"
            ),
            labels=["self-improvement", "automated"],
        )
        print(f"Created self-improvement issue #{issue.number}: {issue.html_url}")
    except Exception as e:
        print(f"Failed to create improvement issue: {e}")


def run_flow():
    flow = SelfEvalFlow()
    flow.kickoff()
    return flow.state


if __name__ == "__main__":
    state = run_flow()
    print(json.dumps(state.model_dump(), indent=2))
