import { Circuit } from "../Circuit";
export function Evidence({ analysis: a }: { analysis: any }) {
  return (
    <>
      <p className="muted">{a.method || a.scope || a.summary_method}</p>
      {a.kind === "firmware" ? (
        <>
          <h3>Functions</h3>
          <div className="row">
            {a.functions.map((f: string) => (
              <code className="badge" key={f}>
                {f}()
              </code>
            ))}
          </div>
          {a.findings.map((f: any, i: number) => (
            <div className="panel finding" key={i}>
              <span className="badge">
                Line {f.line} · {f.type.replaceAll("_", " ")}
              </span>
              <pre>{f.excerpt}</pre><p className="muted">{f.explanation}</p>
            </div>
          ))}
        </>
      ) : a.kind === "circuit" ? (
        <>
          <Circuit analysis={a} />
          <h3>Components</h3>
          <table>
            <thead>
              <tr>
                <th>Reference</th>
                <th>Value</th>
                <th>Declared pins</th>
              </tr>
            </thead>
            <tbody>
              {a.components.map((c: any) => (
                <tr key={c.reference}>
                  <td>{c.reference}</td>
                  <td>{c.value}</td>
                  <td>
                    {c.pins?.length ? (
                      <div className="row">
                        {c.pins.map((pin: any, i: number) => (
                          <span className="badge" key={i}>
                            {pin.number} · {pin.name} ({pin.electrical_type})
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="muted">No embedded pin metadata</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <h3>Nets and connectivity</h3>
          {a.nets.map((n: any, i: number) => (
            <div className="panel" key={i}>
              <strong>{n.name}</strong>
              <div className="row">
                {n.nodes.map((node: any, j: number) => (
                  <span className="badge" key={j}>
                    {node.reference}:{node.pin}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </>
      ) : (
        <>
          {a.summary && <blockquote>{a.summary}</blockquote>}
          {a.characteristics?.length > 0 && (
            <section className="panel">
              <h3>Extracted documented characteristics</h3>
              <p className="muted">
                Explicit statements only. Check source applicability and
                distinguish operating limits from absolute maximum ratings.
              </p>
              {a.characteristics.map((c: any, i: number) => (
                <details key={i}>
                  <summary>
                    {c.kind} · {c.name || c.unit || c.protocols?.join(", ")} ·
                    page {c.page}
                  </summary>
                  <blockquote>{c.excerpt}</blockquote>
                  <dl>
                    {Object.entries(c)
                      .filter(
                        ([key]) =>
                          ![
                            "excerpt",
                            "page",
                            "classification",
                            "kind",
                          ].includes(key),
                      )
                      .map(([key, value]) => (
                        <div key={key}>
                          <dt>{key.replaceAll("_", " ")}</dt>
                          <dd>{String(value)}</dd>
                        </div>
                      ))}
                  </dl>
                </details>
              ))}
            </section>
          )}
          {a.chunks?.map((c: any, i: number) => (
            <details className="panel" key={i}>
              <summary>Source excerpt · page {c.page}</summary>
              <pre>{c.content}</pre>
            </details>
          ))}
        </>
      )}
    </>
  );
}
