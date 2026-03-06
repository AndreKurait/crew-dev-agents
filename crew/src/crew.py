import os
from pathlib import Path

import yaml
from crewai import Agent, Crew, Task, LLM


def load_yaml(name: str) -> dict:
    config_dir = Path(__file__).parent.parent / "config"
    with open(config_dir / name) as f:
        return yaml.safe_load(f)


def build_crew(repo_url: str | None = None) -> Crew:
    model = os.environ.get("BEDROCK_MODEL", "bedrock/anthropic.claude-opus-4-6-v1:0")
    llm = LLM(model=model)

    agents_cfg = load_yaml("agents.yaml")
    tasks_cfg = load_yaml("tasks.yaml")

    repo = repo_url or os.environ.get("REPO_URL", "")

    # Build agents
    agents = {
        name: Agent(llm=llm, **cfg)
        for name, cfg in agents_cfg.items()
    }

    # Build tasks, injecting repo context
    tasks = []
    for name, cfg in tasks_cfg.items():
        agent_name = cfg.pop("agent")
        cfg["description"] = cfg["description"].strip() + f"\n\nTarget repo: {repo}"
        tasks.append(Task(agent=agents[agent_name], **cfg))

    return Crew(
        agents=list(agents.values()),
        tasks=tasks,
        verbose=True,
    )
