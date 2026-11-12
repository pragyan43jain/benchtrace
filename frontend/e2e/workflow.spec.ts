import { test, expect } from "@playwright/test";
import path from "node:path";
test("complete engineering investigation in the browser", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Don’t just debug/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Start an investigation" }).click();
  await page.getByLabel("Name", { exact: true }).fill("Browser Engineer");
  await page
    .getByLabel("Email", { exact: true })
    .fill(`browser-${Date.now()}@example.test`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("browser-test-passphrase");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Your projects" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "New project" }).click();
  await page
    .getByLabel("Project name")
    .fill("ESP32 / Simulated sensor failure");
  await page
    .getByLabel("Description", { exact: true })
    .fill("Reproducible address mismatch. All measurements are simulated.");
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "ESP32 / Simulated sensor failure" }),
  ).toBeVisible();
  const demo = path.resolve("../demo/esp32-i2c");
  await page
    .getByLabel("Evidence file")
    .setInputFiles(path.join(demo, "initial-evidence.zip"));
  await page.getByRole("button", { name: "Upload evidence" }).click();
  await expect(
    page.getByText("Evidence uploaded. Processing has started."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Dismiss notification" }).click();
  await page.getByLabel("Evidence category").selectOption("datasheet");
  await page
    .getByLabel("Evidence file")
    .setInputFiles(path.join(demo, "sensor-datasheet.txt"));
  await page.getByRole("button", { name: "Upload evidence" }).click();
  await expect(
    page.locator(".file-list button").filter({ hasText: "failure.csv" }),
  ).toContainText("ready", { timeout: 120000 });
  await expect(
    page
      .locator(".file-list button")
      .filter({ hasText: "sensor-datasheet.txt" }),
  ).toContainText("ready", { timeout: 120000 });
  await page
    .locator(".file-list button")
    .filter({ hasText: "failure.csv" })
    .click();
  await expect(page.locator(".uplot")).toBeVisible();
  const channel = page.getByRole("checkbox", { name: "SDA", exact: true });
  await channel.uncheck();
  await expect(channel).not.toBeChecked();
  await channel.check();
  await page.getByRole("button", { name: "Pan →" }).click();
  await page.getByRole("button", { name: "Reset zoom" }).click();
  await expect(page.getByText("0x92 NACK", { exact: true })).toBeVisible();
  await page.screenshot({
    path: "../docs/waveform-studio.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Investigations", exact: true })
    .click();
  await page
    .getByLabel("Observed failure")
    .fill("SIMULATED ESP32 sensor does not ACK at configured address.");
  await page
    .getByRole("button", { name: "Create investigation", exact: true })
    .click();
  await page.getByRole("button", { name: "Correlate evidence" }).click();
  await expect(page.locator(".hypothesis").first()).toContainText(
    "Firmware targets an incorrect I2C address",
  );
  await expect(page.locator(".hypothesis").first()).toContainText(
    "sensor-datasheet.txt",
  );
  await page.getByRole("button", { name: "Dismiss notification" }).click();
  await page.screenshot({
    path: "../docs/diagnostic-workspace.png",
    fullPage: false,
  });
  const top = page.locator(".hypothesis").first();
  await top.getByText("Record a test result", { exact: true }).click();
  await top
    .getByLabel("Actual observation")
    .fill(
      "SIMULATED verification: address 0x48 ACKs, original 0x49 NACKs. No physical measurement.",
    );
  await top
    .getByRole("combobox", { name: "Outcome", exact: true })
    .selectOption("confirms");
  await top.getByRole("button", { name: "Record result" }).click();
  await expect(top).toContainText("user-confirmed");
  const download = page.waitForEvent("download");
  await page.getByRole("link", { name: "Export report" }).click();
  expect((await download).suggestedFilename()).toBe("benchtrace-report.md");
  await page.getByRole("button", { name: "Save to knowledge" }).click();
  await expect(
    page.getByText("Report snapshot saved to your private knowledge base."),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Knowledge base", exact: true })
    .click();
  await expect(
    page.getByText(
      "SIMULATED ESP32 sensor does not ACK at configured address.",
      { exact: true },
    ),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator("body")).toHaveJSProperty("scrollWidth", 390);
  await page.screenshot({
    path: "../docs/mobile-workspace.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("login restores a private session and logout removes access", async ({
  page,
}) => {
  const email = `session-${Date.now()}@example.test`;
  const password = "session-restoration-passphrase";
  await page.goto("/");
  await page.getByRole("button", { name: "Start an investigation" }).click();
  await page.getByLabel("Name", { exact: true }).fill("Session Engineer");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Your projects" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Your projects" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Start an investigation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Sign in", exact: true })
    .last()
    .click();
  await expect(
    page.getByRole("heading", { name: "Your projects" }),
  ).toBeVisible();
});

test("processing events are delivered only to the project owner", async ({
  browser,
  baseURL,
}) => {
  const owner = await browser.newContext();
  const stranger = await browser.newContext();
  const stamp = Date.now();
  try {
    for (const [context, name] of [
      [owner, "owner"],
      [stranger, "stranger"],
    ] as const) {
      const r = await context.request.post(`${baseURL}/api/auth/register`, {
        headers: { Origin: baseURL! },
        data: {
          email: `socket-${name}-${stamp}@example.test`,
          name: "Socket " + name,
          password: "socket-isolation-passphrase",
        },
      });
      expect(r.ok()).toBeTruthy();
    }
    const created = await owner.request.post(`${baseURL}/api/projects`, {
      headers: { Origin: baseURL! },
      data: { name: "WebSocket isolation", platform: "ESP32" },
    });
    const project = (await created.json()).id;
    const a = await owner.newPage(),
      b = await stranger.newPage();
    await a.goto("/");
    await b.goto("/");
    for (const page of [a, b])
      await page.evaluate(
        () =>
          new Promise<void>((resolve, reject) => {
            const state = window as any;
            state.testEvents = [];
            state.testSocket = new WebSocket(
              `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/events`,
            );
            state.testSocket.onopen = () => resolve();
            state.testSocket.onerror = () => reject(new Error("Socket failed"));
            state.testSocket.onmessage = (event: MessageEvent) =>
              state.testEvents.push(event.data);
          }),
      );
    const uploaded = await owner.request.post(
      `${baseURL}/api/projects/${project}/files`,
      {
        headers: { Origin: baseURL! },
        multipart: {
          file: {
            name: "main.ino",
            mimeType: "text/plain",
            buffer: Buffer.from("void setup(){Wire.begin(21,22);}"),
          },
          category: "firmware",
        },
      },
    );
    expect(uploaded.status()).toBe(202);
    await expect
      .poll(() => a.evaluate(() => (window as any).testEvents.length), {
        timeout: 30000,
      })
      .toBeGreaterThan(0);
    expect(await b.evaluate(() => (window as any).testEvents)).toEqual([]);
  } finally {
    await owner.close();
    await stranger.close();
  }
});
