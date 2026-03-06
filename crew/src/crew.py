import json
import os
from pathlib import Path

import yaml
from crewai import Agent, Crew, Task, LLM

from src.tools.github_tool import list_open_issues, list_open_prs, add_issue_comment, add_labels
from src.tools.metrics_tool import store_metrics, read_recent_metrics


def load_yaml(name: str) -> dict:
    config_dir = Path(__file__).parent.parent / "config"
    with open(config_dir / name) as f:
        return yaml.safe_load(f)


def build_crew(repo_url: str | None = None) -> Crew:
    model = os.environ.get("BEDROCK_MODEL", "bedrock/anthropic.claude-opus-4-6-v1:0")
    llm = LLM(model=model)
    repo = repo_url or os.environ.get("REPO_URL", "")

    agents_cfg = load_yaml("agents.yaml")
    tasks_cfg = load_yaml("tasks.yaml")

    # Tool assignments per agent
    tool_map = {
        "triager": [list_open_issues, add_issue_comment, add_labels],
        "reviewer": [list_open_prs, add_issue_comment],
        "coder": [list_open_issues, list_open_prs],
        "evolver": [read_recent_metrics, store_metrics],
    }

    agents = {}
    for name, cfg in agents_cfg.items():
        agents[name] = Agent(
            llm=llm,
            tools=tool_map.get(name, []),
            **cfg,
        )

    tasks = []
    for name, cfg in tasks_cfg.items():
        agent_name = cfg.pop("agent")
        cfg["description"] = cfg["description"].strip() + f"\n\nTarget repo: {repo}"
        tasks.append(Task(agent=agents[agent_name], **cfg))

    return Crew(agents=list(agents.values()), tasks=tasks, verbose=True)
