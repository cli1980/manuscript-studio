"""Engine for the test-only echo template; exercises the base engine without translation code."""

from ..src.engine import Engine


class EchoEngine(Engine):
    def stage_prompt(self, state, stage):
        return f"Copy input/{state['source_name']} to output/echo.md and return its path."

    def on_completed(self, state, stage, result):
        if not result["output_path"] or not result["output_path"].startswith("output/"):
            raise ValueError("The echo output belongs under output/.")
        artifact = self.checkpoint(result["output_path"], "echo")
        artifact["chapter_id"] = "whole"
        state["outputs"] = [artifact]
        self._advance_stage(state)
