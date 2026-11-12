import { useEffect, useState } from "react";
import { api } from "../api";
import { Button } from "./ui/button";
export function ProjectPreferences({
  project,
  run,
  busy,
  onSaved,
}: {
  project: any;
  run: (f: () => Promise<void>) => void;
  busy: boolean;
  onSaved: () => Promise<void>;
}) {
  const [history, setHistory] = useState<any[]>([]);
  const [error, setError] = useState("");
  const base = "/projects/" + project.id;
  useEffect(() => {
    api(base + "/history")
      .then(setHistory)
      .catch((e) => setError(e.message));
  }, [base]);
  return (
    <>
      <form
        className="panel settings-form"
        onSubmit={(e) => {
          e.preventDefault();
          const raw = Object.fromEntries(new FormData(e.currentTarget));
          const body = Object.fromEntries(
            Object.entries(raw).map(([k, v]) => [k, Number(v)]),
          );
          run(async () => {
            await api(base + "/preferences", body, "PATCH");
            await onSaved();
            setHistory(await api(base + "/history"));
          });
        }}
      >
        <h2>Analysis defaults for new uploads</h2>
        <p className="muted">
          Defaults apply to future files. Existing captures retain their own
          decoder settings.
        </p>
        <div className="analysis-controls">
          <label>
            Digital threshold (V)
            <input
              type="number"
              name="threshold"
              min="0.01"
              max="100"
              step="0.01"
              required
              defaultValue={project.preferences.threshold}
            />
          </label>
          <label>
            UART baud
            <input
              type="number"
              name="baud"
              min="1"
              max="10000000"
              required
              defaultValue={project.preferences.baud}
            />
          </label>
          <label>
            SPI CPOL
            <select name="cpol" defaultValue={project.preferences.cpol}>
              <option>0</option>
              <option>1</option>
            </select>
          </label>
          <label>
            SPI CPHA
            <select name="cpha" defaultValue={project.preferences.cpha}>
              <option>0</option>
              <option>1</option>
            </select>
          </label>
        </div>
        <Button disabled={busy}>Save analysis defaults</Button>
      </form>
      <details className="panel settings-form">
        <summary>Project history · {history.length} events</summary>
        {error && <p role="alert">{error}</p>}
        {history.map((event) => (
          <div className="timeline" key={event.id}>
            <small>{new Date(event.created_at).toLocaleString()}</small>
            <strong>{event.kind.replaceAll("_", " ")}</strong>
            <pre>{JSON.stringify(event.detail, null, 2)}</pre>
          </div>
        ))}
      </details>
    </>
  );
}
