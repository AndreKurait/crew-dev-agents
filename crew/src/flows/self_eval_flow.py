import json
import os

from crewai.flow.flow import Flow, listen, router, start
from pydantic import BaseModel

from src.crew import build_crew


class FlowState(BaseModel):
    repo_url: str = ""
    retry_count: int = 0
    max_retries: int = 2
    quality_score: float = 0.0
    quality_threshold: float = 0.7
    crew_output: str = ""
    metrics: dict = {}


class SelfEvalFlow(Flow[FlowState]):
    """Run crew → evaluate → loop or finalize."""

    @start()
    def run_crew(self):
        self.state.repo_url = os.environ.get("REPO_URL", self.state.repo_url)
        crew = build_crew(self.state.repo_url)
        result = crew.kickoff()
        self.state.crew_output = str(result)

    @router(run_crew)
    def evaluate(self):
        output = self.state.crew_output
        score = 0.0
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
        }
        if score >= self.state.quality_threshold:
            return "finalize"
        if self.state.retry_count < self.state.max_retries:
            self.state.retry_count += 1
            return "retry"
        return "finalize"

    @listen("retry")
    def retry_crew(self):
        self.run_crew()

    @listen("finalize")
    def finalize(self):
        from src.tools.metrics_tool import store_metrics
        store_metrics.run(json.dumps(self.state.metrics))
        # Create a self-improvement issue if score is low
        if self.state.quality_score < self.state.quality_threshold:
            self._create_improvement_issue()

    def _create_improvement_issue(self):
        """Create a GitHub issue on the platform repo suggesting improvements."""
        try:
            from src.tools.github_tool import _get_github
            gh = _get_github()
            repo = gh.get_repo("AndreKurait/crew-dev-agents")
            repo.create_issue(
                title=f"[Auto] Self-improvement: quality score {self.state.quality_score:.2f}",
                body=(
                    f"## Automated Self-Evaluation Report\n\n"
                    f"**Quality Score**: {self.state.quality_score:.2f} "
                    f"(threshold: {self.state.quality_threshold})\n"
                    f"**Retries**: {self.state.retry_count}\n"
                    f"**Output Length**: {len(self.state.crew_output)}\n\n"
                    f"### Suggested Improvements\n"
                    f"- Review agent backstories for specificity\n"
                    f"- Add more targeted tools\n"
                    f"- Improve task descriptions with concrete examples\n"
                    f"- Add linting, tests, and better error handling\n"
                ),
                labels=["self-improvement", "automated"],
            )
        except Exception as e:
            print(f"Failed to create improvement issue: {e}")


def run_flow():
    flow = SelfEvalFlow()
    flow.kickoff()
    return flow.state


if __name__ == "__main__":
    state = run_flow()
    print(json.dumps(state.model_dump(), indent=2))
