import { afterEach, expect, test, vi } from "vitest";
import { api } from "./api";
afterEach(() => vi.unstubAllGlobals());
test("API surfaces server validation failures", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ error: "Invalid upload" }),
    }),
  );
  await expect(api("/projects")).rejects.toThrow("Invalid upload");
});
test("API retains cookie credentials and sends JSON", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => ({ id: "p" }) });
  vi.stubGlobal("fetch", fetch);
  await expect(api("/projects", { name: "test" })).resolves.toEqual({
    id: "p",
  });
  expect(fetch.mock.calls[0][1].credentials).toBe("same-origin");
  expect(fetch.mock.calls[0][1].body).toBe('{"name":"test"}');
});
