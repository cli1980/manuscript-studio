// Only text actually displayed beside a decision may replace a duplicate in that decision.
export interface ReviewedText { text: string }

const normalize = (text: string) => text.replace(/\r\n?/g, "\n").trim();

export function repeatsReviewedText(text: string, reviewed?: ReviewedText): boolean {
  return !!reviewed && !!normalize(reviewed.text) && normalize(text) === normalize(reviewed.text);
}
