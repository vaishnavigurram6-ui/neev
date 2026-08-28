# neev_pipeline package — ADK discovers the pipeline through this import.
# `adk web` (run from the parent directory) requires the agent package to
# expose `agent` so it can find `neev_pipeline.agent.root_agent`.
from . import agent  # noqa: F401
