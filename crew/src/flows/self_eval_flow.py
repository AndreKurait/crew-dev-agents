import json
import os
import traceback

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
    metrics: dict = {}


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
        score = 0.0
        if self.state.error:
            score = 0.1
        else:
            if output and len(output) > 100:
                score += 0.3
            if "issue_number" in output or "pr_number" in output:
                score += 0.4
            if "error" not in output.lower():
                score += 0.3
        self.state.quality_score = score
        self.state.metrics = {
            "quality_score": score,
            "retry_count": self.state.retry_count,
            "output_length": len(output),
            "error": self.state.error or None,
        }
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
        from src.tools.metrics_tool import store_metrics
        store_metrics.run(json.dumps(self.state.metrics))
        if self.state.quality_score < self.state.quality_threshold:
            self._create_improvement_issue()
        print(f"Flow complete. Score: {self.state.quality_score:.2f}, Error: {self.state.error or 'none'}")

    def _create_improvement_issue(self):
        try:
            from src.tools.github_tool import _get_github, _repo_name
            gh = _get_github()
            repo = gh.get_repo(_repo_name())
            repo.create_issue(
                title=f"[Auto] Self-improvement needed: score {self.state.quality_score:.2f}",
                body=(
                    f"## Automated Self-Evaluation Report\n\n"
                    f"**Quality Score**: {self.state.quality_score:.2f} / {self.state.quality_threshold}\n"
                    f"**Retries**: {self.state.retry_count}\n"
                    f"**Error**: {self.state.error or 'none'}\n\n"
                    f"### Suggested Improvements\n"
                    f"- Add unit tests for crew tools\n"
                    f"- Add linting (ruff/black) to CI pipeline\n"
                    f"- Improve error handling in tools\n"
                    f"- Add README documentation for each component\n"
                    f"- Add type hints and docstrings\n"
                ),
                labels=["self-improvement", "automated"],
            )
            print("Created self-improvement issue")
        except Exception as e:
            print(f"Failed to create improvement issue: {e}")


def run_flow():
    flow = SelfEvalFlow()
    flow.kickoff()
    return flow.state


if __name__ == "__main__":
    state = run_flow()
    print(json.dumps(state.model_dump(), indent=2))
