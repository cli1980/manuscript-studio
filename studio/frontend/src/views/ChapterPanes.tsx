import type { Pane } from "../workflows";
import { CommentableText, type InlineComment } from "./CommentableText";
import { Markdown } from "./Markdown";

// The reading area of the chapter viewer: the panes a workflow defines (translation: original and translation;
// editing: the text being edited), side by side. Panes marked commentable take inline comments.
export function ChapterPanes({ panes, onComments }: {
  panes: Pane[]; onComments: (key: string, comments: InlineComment[]) => void;
}) {
  return (
    <div className={`columns panes-${panes.length}`}>
      {panes.map((pane) => (
        <div key={pane.key} id={pane.reviewTarget} className={pane.awaiting ? "awaiting" : undefined}>
          <h3>{pane.title}{pane.badge && <> <span className={`tag ${pane.awaiting ? "busy" : ""}`}>{pane.badge}</span></>}
            {pane.meta && <> <span className="muted mono">{pane.meta}</span></>}</h3>
          {pane.text == null ? <p className="muted">{pane.note}</p>
            : pane.commentKey
            ? <CommentableText key={pane.commentKey} storageKey={pane.commentKey}
                onChange={(comments) => onComments(pane.commentKey!, comments)}><Markdown text={pane.text} /></CommentableText>
            : <Markdown text={pane.text} />}
        </div>
      ))}
    </div>
  );
}
