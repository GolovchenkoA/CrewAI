# Notes: multi-agent frameworks

- CrewAI organises work as agents (role, goal, backstory), tasks and crews.
- Flows are the event-driven layer: start, listen and router steps with typed state.
- LangGraph models an agent system as an explicit state graph with nodes and edges.
- Hierarchical processes add a manager agent that delegates tasks to workers.
- Guardrails validate a task result and make the agent retry when it fails.
