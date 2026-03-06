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
    evolution_proposals: list = []


class SelfEvalFlow(Flow[FlowState]):
    """Run crew → evaluate → loop or evolve."""

    @start()
    def run_crew(self):
        self.state.repo_url = os.environ.get("REPO_URL", self.state.repo_url)
        crew = build_crew(self.state.repo_url)
        result = crew.kickoff()
        self.state.crew_output = str(result)

    @router(run_crew)
    def evaluate(self):
        """Score the crew output and decide: retry, evolve, or finalize."""
        output = self.state.crew_output
        score = 0.0
        # Simple heuristic scoring — replace with LLM-based eval in production
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
        return "evolve"

    @listen("retry")
    def retry_crew(self):
        """Re-run crew with feedback from previous attempt."""
        self.run_crew()

    @listen("evolve")
    def evolve_config(self):
        """Trigger Evolver agent to propose config changes."""
        from src.tools.metrics_tool import store_metrics
        store_metrics(json.dumps(self.state.metrics))
        # In production: Evolver agent creates a PR on the platform repo
        self.state.evolution_proposals.append({
            "trigger": "quality_below_threshold",
            "score": self.state.quality_score,
            "suggestion": "Review agent backstories and task descriptions for specificity",
        })

    @listen("finalize")
    def finalize(self):
        """Store metrics and complete."""
        from src.tools.metrics_tool import store_metrics
        store_metrics(json.dumps(self.state.metrics))


def run_flow():
    flow = SelfEvalFlow()
    flow.kickoff()
    return flow.state


if __name__ == "__main__":
    state = run_flow()
    print(json.dumps(state.model_dump(), indent=2))
