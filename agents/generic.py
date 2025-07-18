# agent_platform/backend/agents/generic.py

from ..agents.base import BaseAgent

class GenericAgent(BaseAgent):
    def __init__(self, agent_name: str, workflow: dict, tool_registry: dict):
        """
        :param agent_name: Logical name of this agent
        :param workflow:   {"tools": [ { "name": str, "input_from": str, "config": {...} }, ... ]}
        :param tool_registry: mapping tool_name -> tool class or instance
        """
        self.agent_name = agent_name
        self.workflow = workflow
        self.tool_registry = tool_registry

    @classmethod
    def from_config(cls, config: dict, tool_registry: dict):
        # when loading from DB we don't have a file-based name
        return cls(agent_name="custom_from_db", workflow=config, tool_registry=tool_registry)

    def run(self, query: str, session_id: str) -> str:
        # validate top‐level structure
        if not isinstance(self.workflow, dict) or "tools" not in self.workflow:
            raise ValueError(
                "[❌ ERROR] Invalid workflow: expected a dict with key 'tools'."
            )

        context = {"query": query, "session_id": session_id}
        previous_output = query

        print(f"[GenericAgent] 🏁 Starting workflow for: {self.agent_name}")

        for idx, step in enumerate(self.workflow["tools"], start=1):
            tool_name = step.get("name")
            input_from = step.get("input_from", "query")
            config = step.get("config", {})

            # fetch the actual text to feed into this tool
            input_data = context.get(input_from, previous_output)

            print(
                f"[GenericAgent] 🔧 Step #{idx}: Tool='{tool_name}' "
                f"| input_from='{input_from}' → '{input_data}' "
                f"| config={config}"
            )

            tool_def = self.tool_registry.get(tool_name)
            if not tool_def:
                available = ", ".join(self.tool_registry.keys())
                raise ValueError(
                    f"[❌ ERROR] Tool '{tool_name}' not found. "
                    f"Available: [{available}]"
                )

            # either a class or a pre‐instantiated object
            if isinstance(tool_def, type):
                tool_instance = tool_def()
            else:
                tool_instance = tool_def

            try:
                # new signature: run(text, context, config)
                output = tool_instance.run(input_data, context, config)
                print(f"[GenericAgent] ✅ Step #{idx} '{tool_name}' output: {output}")
            except Exception as e:
                print(f"[GenericAgent] ❌ Step #{idx} '{tool_name}' failed: {e}")
                raise RuntimeError(f"Execution failed in '{tool_name}': {e}")

            # store for downstream steps
            context[tool_name] = output
            previous_output = output

        return previous_output
