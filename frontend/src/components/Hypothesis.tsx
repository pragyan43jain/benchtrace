import { FlaskConical, Check } from "lucide-react";
import { Button } from "./ui/button";
export function Hypothesis({
  hypothesis: h,
  onTest,
  busy,
}: {
  hypothesis: any;
  onTest: (data: any) => void;
  busy: boolean;
}) {
  const a = h.assessment;
  return (
    <article className="hypothesis panel">
      <header>
        <span className="rank">{h.rank.toString().padStart(2, "0")}</span>
        <div>
          <h3>{h.title}</h3>
          <span className="muted">
            Evidence balance {a.evidence_balance} · {a.ranking_method} ·{" "}
            {h.status === "confirmed" ? "user-confirmed" : h.status}
          </span>
        </div>
        <span
          className={"badge " + (h.status === "confirmed" ? "green" : "amber")}
        >
          {h.status}
        </span>
      </header>
      <div className="evidence-columns">
        {[
          ["supporting_evidence", "Supporting evidence"],
          ["contradictory_evidence", "Contradicting evidence"],
        ].map(([key, label]) => (
          <div key={key}>
            <h4>{label}</h4>
            {a[key].length ? (
              a[key].map((e: any, i: number) => (
                <blockquote key={i}>
                  <small>
                    {e.source}
                    {e.page ? ` · page ${e.page}` : ""}
                    {e.line ? ` · line ${e.line}` : ""}
                  </small>
                  <p>{e.excerpt}</p>
                </blockquote>
              ))
            ) : (
              <p className="muted">No cited evidence yet.</p>
            )}
          </div>
        ))}
      </div>
      <div className="next-test">
        <span className="eyebrow">
          <FlaskConical size={13} /> NEXT VERIFICATION TEST
        </span>
        <p>{a.recommended_test}</p>
        <dl>
          <div>
            <dt>Confirms if</dt>
            <dd>{a.confirms_if}</dd>
          </div>
          <div>
            <dt>Rejects if</dt>
            <dd>{a.rejects_if}</dd>
          </div>
        </dl>
      </div>
      <p className="muted">Unknown: {a.unknowns.join(" ")}</p>
      <details>
        <summary>Record a test result and update assessment</summary>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = Object.fromEntries(new FormData(e.currentTarget));
            onTest({ ...f, hypothesis_id: h.id });
          }}
        >
          <label>
            Actual observation
            <textarea
              name="observation"
              minLength={5}
              required
              placeholder="Record the instrument, setup, measured result, and whether this was simulated."
            />
          </label>
          <label>
            Outcome
            <select name="outcome">
              <option value="inconclusive">Inconclusive</option>
              <option value="supports">Supports hypothesis</option>
              <option value="confirms">User confirms hypothesis</option>
              <option value="rejects">Rejects hypothesis</option>
            </select>
          </label>
          <Button disabled={busy}>
            <Check size={15} />
            Record result
          </Button>
        </form>
      </details>
    </article>
  );
}
