import { useEffect, useRef, useState } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import {
  ResponsiveContainer,
  BarChart,
  LineChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import { Button } from "./components/ui/button";
export function Waveform({ analysis: a }: { analysis: any }) {
  const host = useRef<HTMLDivElement>(null);
  const plot = useRef<uPlot | null>(null);
  const names = Object.keys(a.channels);
  const [range, setRange] = useState<[number, number]>([
    a.time[0],
    a.time[a.time.length - 1],
  ]);
  const [visible, setVisible] = useState(names);
  useEffect(() => {
    if (!host.current) return;
    const colors = ["#4f8cff", "#22c5a5", "#f59e0b", "#bd9bff"];
    const p = new uPlot(
      {
        width: host.current.clientWidth,
        height: 310,
        scales: { x: { time: false } },
        cursor: { drag: { x: true, y: false } },
        axes: [
          {
            stroke: "#94a3b8",
            grid: { stroke: "#202735" },
            label: "Time (seconds)",
          },
          {
            stroke: "#94a3b8",
            grid: { stroke: "#202735" },
            label: "Voltage (V)",
          },
        ],
        series: [
          {},
          ...names.map((n, i) => ({
            label: n.toUpperCase(),
            stroke: colors[i % 4],
            width: 1.5,
            paths: uPlot.paths.stepped!({ align: 1 }),
          })),
        ],
        hooks: {
          setScale: [
            (p) => {
              if (p.scales.x.min !== undefined && p.scales.x.max !== undefined)
                setRange([p.scales.x.min, p.scales.x.max]);
            },
          ],
        },
      },
      [a.time, ...names.map((n) => a.channels[n].samples)],
      host.current,
    );
    plot.current = p;
    const observer = new ResizeObserver(() => {
      if (host.current)
        p.setSize({ width: host.current.clientWidth, height: 310 });
    });
    observer.observe(host.current);
    return () => {
      observer.disconnect();
      p.destroy();
    };
  }, [a]);
  const shift = (direction: number) => {
    const size = range[1] - range[0];
    plot.current?.setScale("x", {
      min: range[0] + size * 0.25 * direction,
      max: range[1] + size * 0.25 * direction,
    });
  };
  return (
    <>
      <div className="toolbar">
        <div className="row">
          {names.map((n, i) => (
            <label className="check" key={n}>
              <input
                type="checkbox"
                checked={visible.includes(n)}
                onChange={(e) => {
                  plot.current?.setSeries(i + 1, { show: e.target.checked });
                  setVisible(
                    e.target.checked
                      ? [...visible, n]
                      : visible.filter((x) => x !== n),
                  );
                }}
              />
              {n.toUpperCase()}
            </label>
          ))}
        </div>
        <div className="row">
          <Button variant="outline" onClick={() => shift(-1)}>
            ← Pan
          </Button>
          <Button variant="outline" onClick={() => shift(1)}>
            Pan →
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              plot.current?.setScale("x", {
                min: a.time[0],
                max: a.time[a.time.length - 1],
              })
            }
          >
            Reset zoom
          </Button>
        </div>
      </div>
      <div ref={host} className="waveform" />
      <p className="muted">
        Drag to select a time range. Cursor values appear in the legend. Δt ={" "}
        {((range[1] - range[0]) * 1e6).toFixed(2)} µs.{" "}
        {a.preview_truncated
          ? "Display is reduced; analysis uses the full capture."
          : ""}
      </p>
      <div className="metric-grid">
        {names.map((n) => (
          <div className="panel" key={n}>
            <h3>{n.toUpperCase()}</h3>
            <dl>
              {Object.entries(a.channels[n].statistics)
                .filter(([k]) =>
                  [
                    "min",
                    "max",
                    "rms",
                    "sample_rate_hz",
                    "peak_count",
                    "noise_estimate_v",
                    "dominant_frequency_hz",
                  ].includes(k),
                )
                .map(([k, v]) => (
                  <div key={k}>
                    <dt>{k.replaceAll("_", " ")}</dt>
                    <dd>
                      {typeof v === "number" ? v.toPrecision(5) : String(v)}
                    </dd>
                  </div>
                ))}
            </dl>
            <p className="muted">
              Threshold crossings: {a.channels[n].threshold_crossings}
            </p>
            {a.channels[n].statistics.moving_average_time && (
              <details>
                <summary>Moving-average filter</summary>
                <p className="muted">
                  {a.channels[n].statistics.moving_average_method}
                </p>
                <div className="spectrum">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={a.channels[n].statistics.moving_average.map(
                        (value: number, index: number) => ({
                          time: a.channels[n].statistics.moving_average_time[
                            index
                          ],
                          voltage: value,
                        }),
                      )}
                    >
                      <XAxis
                        dataKey="time"
                        type="number"
                        tick={{ fill: "#94a3b8", fontSize: 9 }}
                      />
                      <YAxis tick={{ fill: "#94a3b8", fontSize: 9 }} />
                      <Tooltip
                        contentStyle={{
                          background: "#171e2b",
                          borderColor: "#303d51",
                        }}
                      />
                      <Line
                        type="linear"
                        dataKey="voltage"
                        stroke="#22c5a5"
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </details>
            )}
            {a.channels[n].statistics.spectrum && (
              <details>
                <summary>FFT peaks (Hann window)</summary>
                <div className="spectrum">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={a.channels[n].statistics.spectrum.slice(0, 10)}
                    >
                      <XAxis
                        dataKey="hz"
                        tick={{ fill: "#94a3b8", fontSize: 9 }}
                      />
                      <YAxis tick={{ fill: "#94a3b8", fontSize: 9 }} />
                      <Tooltip
                        contentStyle={{
                          background: "#171e2b",
                          borderColor: "#303d51",
                        }}
                      />
                      <Bar dataKey="amplitude" fill="#4f8cff" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </details>
            )}
          </div>
        ))}
      </div>
      <h3>Protocol analysis</h3>
      {Object.entries(a.protocols).map(([name, p]: [string, any]) => (
        <section className="panel" key={name}>
          <div className="row">
            <h3>{name.toUpperCase()}</h3>
            <span className={"badge " + (p.reliable ? "green" : "amber")}>
              {p.reliable ? "Decodable capture" : "Reliability warning"}
            </span>
          </div>
          {p.warnings.map((x: string) => (
            <p className="warning" key={x}>
              {x}
            </p>
          ))}
          <p className="muted">{p.limitations || p.format}</p>
          {p.frames.map((f: any, i: number) => (
            <div className="protocol-row" key={i}>
              <code>{(f.start ?? f.time ?? 0).toFixed(7)} s</code>
              {f.address !== undefined ? (
                <>
                  <span>
                    Address{" "}
                    <strong>0x{f.address.toString(16).padStart(2, "0")}</strong>{" "}
                    · {f.direction}
                  </span>
                  {f.bytes.map((b: any, j: number) => (
                    <span
                      className={"badge " + (b.ack ? "green" : "red")}
                      key={j}
                    >
                      0x{b.value.toString(16)} {b.ack ? "ACK" : "NACK"}
                    </span>
                  ))}
                </>
              ) : (
                <span>
                  Byte 0x{f.value.toString(16)}{" "}
                  {f.framing_error ? "— framing error" : ""}
                </span>
              )}
            </div>
          ))}
        </section>
      ))}
    </>
  );
}
