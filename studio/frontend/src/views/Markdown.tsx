import { Children, type ReactNode } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

// The studio's one Markdown renderer for agent-written and workflow Markdown (chapters, brief documents,
// summaries, library files). react-markdown never injects raw HTML; GitHub-flavored tables are enabled.

// A heading such as "C — accepted" or "A — rejected" gets a status tag.
function withStatus(children: ReactNode) {
  const text = Children.toArray(children).join("");
  const status = typeof text === "string" ? text.match(/^(.*?)\s*[—-]\s*(accepted|rejected)\s*$/i) : null;
  if (!status) return children;
  return <>{status[1]} <span className={`tag md-${status[2].toLowerCase()}`}>{status[2].toLowerCase()}</span></>;
}

// Document headings sit below the page's own headings, so levels shift down by two.
const heading = (Tag: "h3" | "h4" | "h5" | "h6") =>
  ({ children }: { children?: ReactNode }) => <Tag>{withStatus(children)}</Tag>;

const components: Components = {
  h1: heading("h3"), h2: heading("h4"), h3: heading("h5"), h4: heading("h6"), h5: heading("h6"), h6: heading("h6"),
  // Links in workspace documents point at files the browser cannot open; show the target as a tooltip.
  a: ({ children, href }) => <span className="md-link" title={href}>{children}</span>,
  table: ({ children }) => <div className="md-table"><table>{children}</table></div>,
};

export function Markdown({ text }: { text: string }) {
  return <div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{text}</ReactMarkdown></div>;
}
