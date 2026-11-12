import { useState } from "react";
import { api } from "../api";
import { Button } from "./ui/button";
export function Knowledge({
  entries,
  projects,
  onChange,
  run,
  busy,
}: {
  entries: any[];
  projects: any[];
  onChange: (v: any[]) => void;
  run: (f: () => Promise<void>) => void;
  busy: boolean;
}) {
  const [components, setComponents] = useState<any[] | null>(null);
  const [project, setProject] = useState("");
  const [verified, setVerified] = useState(false);
  const [query, setQuery] = useState("");
  async function search() {
    onChange(
      await api(
        "/knowledge?" +
          new URLSearchParams({
            q: query,
            project,
            verified: String(verified),
          }),
      ),
    );
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">REUSE WHAT YOU LEARN</span>
          <h1>Engineering knowledge</h1>
          <p className="muted">
            Private procedures, component references and investigation
            snapshots.
          </p>
        </div>
      </div>
      <form
        className="panel"
        onSubmit={(e) => {
          e.preventDefault();
          run(search);
        }}
      >
        <div className="search-form">
          <input
            aria-label="Search knowledge"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search faults, procedures or measurements…"
          />
          <Button disabled={busy}>Search</Button>
        </div>
        <div className="row">
          <label>
            Project scope
            <select
              value={project}
              onChange={(e) => {
                setProject(e.target.value);
                setComponents(null);
              }}
            >
              <option value="">All my projects</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={verified}
              onChange={(e) => setVerified(e.target.checked)}
            />
            User-confirmed solutions only
          </label>
          <Button
            type="button"
            variant="outline"
            disabled={!project || busy}
            onClick={() =>
              run(async () =>
                setComponents(
                  await api("/projects/" + project + "/components"),
                ),
              )
            }
          >
            Browse components
          </Button>
        </div>
      </form>
      {components && (
        <section className="panel">
          <h2>Imported component references</h2>
          <p className="muted">
            Extracted from the selected project's circuit files; physical
            installation is unverified.
          </p>
          {components.length ? (
            <table>
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Value</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {components.map((c) => (
                  <tr key={c.id}>
                    <td>{c.reference}</td>
                    <td>{c.properties.value}</td>
                    <td>{c.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No supported circuit components have been imported.</p>
          )}
        </section>
      )}
      <details className="panel">
        <summary>Save a troubleshooting procedure</summary>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = Object.fromEntries(new FormData(e.currentTarget));
            run(async () => {
              await api("/projects/" + f.project + "/knowledge", {
                title: f.title,
                content: f.content,
              });
              await search();
            });
          }}
        >
          <label>
            Procedure project
            <select name="project" required>
              <option value="">Select a private project</option>
              {projects.map((p) => (
                <option value={p.id} key={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Procedure title
            <input name="title" required minLength={3} maxLength={200} />
          </label>
          <label>
            Steps, expected results and safety constraints
            <textarea
              name="content"
              required
              minLength={10}
              maxLength={20000}
            />
          </label>
          <p className="muted">
            A saved procedure is unverified. Confirmed solutions come from
            explicitly recorded investigation tests.
          </p>
          <Button disabled={busy}>Save procedure</Button>
        </form>
      </details>
      {entries.length ? (
        entries.map((k) => (
          <details className="panel" key={k.id}>
            <summary>{k.title}</summary>
            <div className="row">
              <span className="badge">{k.kind || "investigation"}</span>
              <span
                className={
                  "badge " +
                  (k.verification === "user_confirmed" ? "green" : "amber")
                }
              >
                {k.verification === "user_confirmed"
                  ? "User-confirmed snapshot"
                  : "Unverified"}
              </span>
            </div>
            <pre className="report-preview">{k.content}</pre>
          </details>
        ))
      ) : (
        <section className="empty">
          <h2>No matching knowledge yet</h2>
          <p>
            Save an investigation report or a troubleshooting procedure, or
            broaden the search.
          </p>
        </section>
      )}
    </>
  );
}
