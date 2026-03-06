import os
import sys

from src.crew import build_crew


def main():
    repo_url = os.environ.get("REPO_URL")
    if not repo_url:
        print("ERROR: REPO_URL environment variable required", file=sys.stderr)
        sys.exit(1)

    crew = build_crew(repo_url)
    result = crew.kickoff()
    print(result)


if __name__ == "__main__":
    main()
