import { readFileSync } from "node:fs";

// The host supplies a stage-specific schema; only this tool can complete a turn.
export default function (pi) {
  const schema = JSON.parse(readFileSync(process.env.MANUSCRIPT_PI_SCHEMA, "utf8"));
  pi.registerTool({
    name: "workflow_result",
    label: "Workflow Result",
    description: "Finish the current workflow operation with its structured result. Call this alone as your final action.",
    parameters: schema,
    async execute(_id, result) {
      return {
        content: [{ type: "text", text: "Workflow operation returned to the host for validation." }],
        details: { workflow_result: result },
        terminate: true,
      };
    },
  });
}
