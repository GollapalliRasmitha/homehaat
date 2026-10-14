import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

import { forgetAwake, wakeServer } from "./wake.ts";

beforeEach(forgetAwake);

const reply = (status: number) => new Response("{}", { status });

test("an awake server answers at once", async () => {
  let calls = 0;
  const ok = await wakeServer({ fetcher: async () => (calls++, reply(200)), pauseMs: 0 });
  assert.equal(ok, true);
  assert.equal(calls, 1);
});

test("keeps asking while the host says the server is starting", async () => {
  const answers = [502, 503, 200];
  const seen: string[] = [];
  const ok = await wakeServer({
    fetcher: async (url) => (seen.push(url), reply(answers.shift()!)),
    pauseMs: 0,
  });
  assert.equal(ok, true);
  assert.deepEqual(seen, ["/api/health/", "/api/health/", "/api/health/"]); // only the harmless check
});

test("no reply at all counts as not awake yet", async () => {
  let calls = 0;
  const ok = await wakeServer({
    fetcher: async () => {
      calls++;
      if (calls < 3) throw new TypeError("Failed to fetch");
      return reply(200);
    },
    pauseMs: 0,
  });
  assert.equal(ok, true);
  assert.equal(calls, 3);
});

test("gives up after the deadline", async () => {
  let clock = 0;
  const ok = await wakeServer({
    fetcher: async () => ((clock += 40_000), reply(502)),
    now: () => clock,
    deadlineMs: 100_000,
    pauseMs: 0,
  });
  assert.equal(ok, false);
});

test("doesn't ask again right after the server answered", async () => {
  await wakeServer({ fetcher: async () => reply(200), pauseMs: 0 });
  let calls = 0;
  assert.equal(await wakeServer({ fetcher: async () => (calls++, reply(200)) }), true);
  assert.equal(calls, 0);
});
