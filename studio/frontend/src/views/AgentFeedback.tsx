import { useEffect, useState } from "react";
import type { Gate } from "../api";
import { TextBlock } from "./common";
import { Markdown } from "./Markdown";
import { SheetReview } from "./SheetReview";
import { CommentSummary, composeComments, type InlineComment } from "./CommentableText";
import type { ReviewedText } from "../reviewText";

// The reusable exchange with the agent for any workflow's decision (translation advice, chapter approval, editorial
// reviews, apply authorizations, questions). It shows the conversation so far, then a body by shape: the item-by-item
// review for an approval sheet; otherwise the offered commands as buttons and a feedback box (or inline comments
// when the page offers them). It only composes the exact reply; the server validates it.
export function AgentFeedback({ gate, agent, onReply, busy = false, commandLabels = {}, comments, commentLabel, runId, reviewedText, message }: {
  gate: Gate;
  agent: string;  // Who answers, e.g. "translator" or "editor" (see WorkflowUI.agentName).
  onReply: (text: string) => void;
  busy?: boolean;
  commandLabels?: Record<string, string>;
  // Inline comments drafted on the text under review, when the page offers them; sent as the feedback.
  comments?: InlineComment[];
  commentLabel?: string;
  runId?: string;
  reviewedText?: ReviewedText;
  // A workflow-owned request when the viewer already presents the complete text being approved.
  message?: string;
}) {
  const [text, setText] = useState("");
  useEffect(() => setText(""), [gate.id]);
  const name = agent.charAt(0).toUpperCase() + agent.slice(1);
  const label = (command: string) => commandLabels[command] ?? command.charAt(0).toUpperCase() + command.slice(1);
  return (
    <div className="agent-feedback">
      {gate.answer_to && (
        <div className="conversation"><div className="label">Your feedback</div><TextBlock text={gate.answer_to.text} /></div>
      )}
      {/* An approval sheet carries everything the reviewer needs; otherwise the agent's message is the request. */}
      {gate.sheet ? <SheetReview key={gate.id} sheet={gate.sheet} busy={busy} onSubmit={onReply} runId={runId}
        reviewedText={reviewedText} /> : (
        <>
          <div className="agent-message">
            <div className="label">{message != null ? "Review" : gate.answer_to ? `${name}'s answer` : name}</div>
            <Markdown text={message ?? gate.message} />
          </div>
          {gate.commands.length > 0 && (
            <div className="row">
              {gate.commands.map((command) => (
                <button key={command} className="primary" disabled={busy} onClick={() => onReply(command)}>{label(command)}</button>
              ))}
            </div>
          )}
          {comments ? (
            <CommentSummary comments={comments} general={text} onGeneral={setText} busy={busy} sendLabel="Send feedback"
              hint={`Select text in ${commentLabel ?? "the text"} to comment on it.`}
              onSend={() => onReply(composeComments(comments, text, commentLabel))} />
          ) : (
            <div className="feedback-box">
              <textarea rows={4} value={text} onChange={(e) => setText(e.target.value)}
                placeholder={gate.commands.length ? `Feedback or questions for the ${agent} (does not approve)` : "Your answer"} />
              <button disabled={busy || !text.trim()} onClick={() => onReply(text)}>
                {gate.commands.length ? "Send feedback" : "Send answer"}</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
