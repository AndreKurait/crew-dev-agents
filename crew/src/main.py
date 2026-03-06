import os
import sys


def main():
    repo_url = os.environ.get("REPO_URL")
    if not repo_url:
        print("ERROR: REPO_URL environment variable required", file=sys.stderr)
        sys.exit(1)

    mode = os.environ.get("CREW_MODE", "flow")

    if mode == "flow":
        from src.flows.self_eval_flow import run_flow
        state = run_flow()
        print(f"Flow complete. Quality: {state.quality_score:.2f}")
    else:
        from src.crew import build_crew
        crew = build_crew(repo_url)
        result = crew.kickoff()
        print(result)


if __name__ == "__main__":
    main()
