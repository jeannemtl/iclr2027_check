---
title: "Block Drill Exam — Set 5 (hardest)"
subtitle: "Ten blocks; each has exactly one real defect or none; the decoys are strong"
date: "October 2026"
---

**How to run it.** Same method. 12 minutes per block. Five of ten are clean. Write the verdict before uncovering; the point is calibration.

# Block 1 — Async queue drain

```ts
1  class Drain {
2    private q: Array<() => Promise<void>> = [];
3    private running = false;
4    push(task: () => Promise<void>) { this.q.push(task); void this.run(); }
5    private async run() {
6      if (this.running) return;
7      this.running = true;
8      try {
9        while (this.q.length) await this.q.shift()!();
10     } finally {
11       this.running = false;
12     }
13   }
14 }
```

**Requirement:** tasks run one at a time, in order, each awaited; a throwing task does not stop later tasks.

**Notes**

| Line | Note |
| --- | --- |
| 4 | `void this.run()`: explicit fire-and-forget; `run` never rejects? see 9 |
| 6–7 | guard then set, no await between: safe |
| 9 | `shift()!` justified by `length`; each task awaited: sequential, in order |
| 9 | if a task THROWS, the `while` exits via the exception, `finally` resets `running`, and `run()` rejects: the `void` on line 4 means that rejection is unhandled, AND the remaining tasks in `q` are not run until the next `push` |
| 10–11 | `finally` resets the flag: good |

**Findings**

1. Line 9: a throwing task aborts the loop and leaves queued tasks stranded, plus an unhandled rejection via `void`; wrap the call: `try { await task() } catch (e) { report(e) }` inside the loop.

**Confidence 3 · Request changes.** Everything else is right.

# Block 2 — Sorted insert

```ts
1  function insertSorted(arr: number[], x: number): void {
2    let lo = 0, hi = arr.length;
3    while (lo < hi) {
4      const mid = (lo + hi) >>> 1;
5      if (arr[mid] < x) lo = mid + 1; else hi = mid;
6    }
7    arr.splice(lo, 0, x);
8  }
```

**Requirement:** insert `x` into an ascending array in place, keeping it sorted; stable for equal values (new value after existing equals).

**Notes**

| Line | Note |
| --- | --- |
| 2 | `hi` exclusive |
| 4 | `>>> 1` is integer halving; no overflow for array lengths |
| 5 | `arr[mid] < x` → go right; equal → go left: finds the FIRST index with value ≥ x: that places the new value BEFORE existing equals |
| 7 | `splice` mutates in place: required |

**Findings**

1. Line 5: for stability "after existing equals" the comparison must be `<=` (upper bound), not `<`.

**Confidence 4 · Request one change.** Binary search is otherwise correct, including the `>>> 1`.

# Block 3 — Token bucket

```ts
1  class Bucket {
2    private tokens: number;
3    private last: number;
4    constructor(private cap: number, private perSec: number, private now = Date.now) {
5      this.tokens = cap; this.last = now();
6    }
7    take(n = 1): boolean {
8      const t = this.now();
9      this.tokens = Math.min(this.cap, this.tokens + ((t - this.last) / 1000) * this.perSec);
10     this.last = t;
11     if (this.tokens < n) return false;
12     this.tokens -= n;
13     return true;
14   }
15 }
```

**Requirement:** classic token bucket; `take(n)` succeeds if `n` tokens available; refills at `perSec`; never exceeds `cap`.

**Notes**

| Line | Note |
| --- | --- |
| 4 | injectable clock; `private now = Date.now` as a parameter property |
| 9 | refill proportional to elapsed; clamped by `cap`; computed BEFORE the check: correct |
| 10 | `last` updated even on failure: correct (elapsed time was already credited) |
| 11–12 | boundary: `tokens < n` fails; `tokens === n` succeeds and leaves 0: correct |
| 7 | `n <= 0` or `NaN`: `tokens < NaN` false → "succeeds", `tokens -= NaN` → `NaN` forever (edge) |

**Findings**

- Edge: validate `n` is a positive finite number.

**Confidence 5 · Approve.** The float arithmetic here is intended; tokens are a rate, not money.

# Block 4 — Deep get

```ts
1  function get(obj: unknown, path: string): unknown {
2    return path.split(".").reduce((o, k) => (o as any)?.[k], obj);
3  }
```

**Requirement:** `get(o, "a.b.c")` returns the nested value or `undefined` if any step is missing; must not throw.

**Notes**

| Line | Note |
| --- | --- |
| 2 | `reduce` from `obj`; each step `?.[k]` returns `undefined` on a nullish accumulator and keeps going; `undefined?.["x"]` is `undefined`; never throws |
| 2 | `(o as any)` is the one cast; the function's contract is `unknown` in, `unknown` out, so the hole is contained |
| 2 | `path = ""` → `[""]` → `obj[""]`: `undefined` unless there is an empty-string key (edge, acceptable) |
| 2 | `"__proto__"` in the path reads the prototype (read-only, no pollution) |

**Findings**

- None.

**Confidence 5 · Approve.** The `as any` is contained and necessary.

# Block 5 — Semaphore with timeout

```ts
1  class Sem {
2    private free: number; private waiters: Array<() => void> = [];
3    constructor(n: number) { this.free = n; }
4    async acquire(timeoutMs: number): Promise<void> {
5      if (this.free > 0) { this.free--; return; }
6      await new Promise<void>((resolve, reject) => {
7        const t = setTimeout(() => reject(new Error("timeout")), timeoutMs);
8        this.waiters.push(() => { clearTimeout(t); resolve(); });
9      });
10   }
11   release() {
12     const w = this.waiters.shift();
13     if (w) w(); else this.free++;
14   }
15 }
```

**Requirement:** `acquire` gets a permit or rejects after `timeoutMs`; `release` hands the permit directly to the next waiter or returns it.

**Notes**

| Line | Note |
| --- | --- |
| 5 | fast path, sync |
| 7–8 | timeout rejects; the waiter callback clears the timeout and resolves |
| 13 | permit handed directly to a waiter (no `free++`), so the count stays right: correct, and it is the fix for Set 3 Block 5 |
| 7 vs 12 | if the timeout FIRES, the waiter's closure is still in `waiters`; a later `release()` shifts it and calls it: `clearTimeout` on a fired timer is harmless, `resolve()` on a rejected Promise is ignored, BUT the permit was handed to a waiter that already gave up: the permit is LOST (neither `free++` nor a live acquirer) |

**Findings**

1. Lines 7/12: on timeout, remove the waiter from `waiters` (or mark it dead and have `release` skip dead waiters and return the permit); otherwise each timed-out waiter permanently consumes one permit.

**Confidence 3 · Request changes.** Subtle; the hand-off pattern is otherwise correct.

# Block 6 — Immutable update

```ts
1  type State = { users: Record<string, { name: string; tags: string[] }> };
2  function addTag(state: State, id: string, tag: string): State {
3    const user = state.users[id];
4    if (!user) return state;
5    return {
6      ...state,
7      users: { ...state.users, [id]: { ...user, tags: [...user.tags, tag] } },
8    };
9  }
```

**Requirement:** return a new state with the tag appended; never mutate the input; unknown id returns the same state object.

**Notes**

| Line | Note |
| --- | --- |
| 4 | returns the same reference for unknown id: required |
| 5–8 | new outer, new `users`, new user, new `tags` array: every level on the changed path is copied; other users remain shared (correct and intended for structural sharing) |
| 3 | `state.users[id]` with a user-controlled `id` of `"constructor"`: `user` is a function, truthy, `user.tags` is `undefined`, `[...undefined]` THROWS |

**Findings**

1. Line 3–4: `Record` on a plain object; `id = "constructor"` passes the `!user` check and throws at `[...user.tags]`; use `Object.hasOwn(state.users, id)` or a `Map`.

**Confidence 4 · Request one change.** The immutable update itself is textbook.

# Block 7 — Exponential moving average

```ts
1  function ema(values: number[], alpha: number): number[] {
2    if (values.length === 0) return [];
3    const out = [values[0]];
4    for (let i = 1; i < values.length; i++) out.push(alpha * values[i] + (1 - alpha) * out[i - 1]);
5    return out;
6  }
```

**Requirement:** EMA with smoothing `alpha` in (0, 1]; first output equals first input; output length equals input length.

**Notes**

| Line | Note |
| --- | --- |
| 2 | empty handled |
| 3 | seed with first value |
| 4 | standard recurrence; `out[i - 1]` always exists; `i < length` correct |
| 1 | `alpha` not validated; `alpha = 0` returns a constant series; `alpha > 1` oscillates; `NaN` poisons (edge) |

**Findings**

- Edge: validate `0 < alpha <= 1`.

**Confidence 5 · Approve.**

# Block 8 — Dedupe concurrent requests

```ts
1  const pending = new Map<string, Promise<Response>>();
2  function dedupedFetch(url: string): Promise<Response> {
3    const p = pending.get(url) ?? fetch(url).finally(() => pending.delete(url));
4    pending.set(url, p);
5    return p;
6  }
```

**Requirement:** identical concurrent `fetch`es share one request; once settled, the next call fetches again.

**Notes**

| Line | Note |
| --- | --- |
| 3 | `??`: reuse if present, else start and schedule removal on settle; `.finally` returns a new Promise that settles with the same outcome |
| 4 | re-sets the SAME `p` on a hit (harmless) or the new one on a miss |
| 3 | `.finally` deletes by `url`; if a THIRD call arrived after the first settled but... no: the delete happens in the finally, and the next `get` after that misses: correct |
| 3 | `Response` body can be consumed once; two callers sharing one `Response` and both calling `.json()` → the second throws "body used already" (contract issue, not this function's bug; note it) |

**Findings**

- Note: sharing a `Response` object means only one caller can read the body; callers must `.clone()` or the function should share the parsed result instead. Depending on the requirement wording ("share one request") this is acceptable.

**Confidence 4 · Approve with a note.**

# Block 9 — Windowed max

```ts
1  function windowMax(a: number[], k: number): number[] {
2    const out: number[] = [], dq: number[] = [];
3    for (let i = 0; i < a.length; i++) {
4      while (dq.length && a[dq[dq.length - 1]] <= a[i]) dq.pop();
5      dq.push(i);
6      if (dq[0] <= i - k) dq.shift();
7      if (i >= k - 1) out.push(a[dq[0]]);
8    }
9    return out;
10 }
```

**Requirement:** sliding-window maximum, window `k` ≥ 1; output length `n - k + 1`.

**Notes**

| Line | Note |
| --- | --- |
| 2 | `dq` holds indices, decreasing values |
| 4 | pop smaller-or-equal from the back: monotonic deque; `<=` is fine (ties keep the newer index, which lasts longer) |
| 6 | evict the front if it left the window: `dq[0] <= i - k` is the correct boundary (index `i - k` is outside a window ending at `i`) |
| 7 | start emitting once the first full window exists: `i >= k - 1`: correct |
| 1 | `k > a.length` → empty output (correct: `n - k + 1 < 1`); `k <= 0` unvalidated |

**Findings**

- Edge: validate `k >= 1`.

**Confidence 5 · Approve.** Every boundary here is right; check each one against `k = 1` and `k = n`.

# Block 10 — Cancellable interval

```ts
1  function every(ms: number, fn: () => void): () => void {
2    let id: ReturnType<typeof setInterval> | undefined = setInterval(fn, ms);
3    return () => { if (id !== undefined) { clearInterval(id); id = undefined; } };
4  }
```

**Requirement:** run `fn` every `ms`; the returned function cancels; calling cancel twice is safe.

**Notes**

| Line | Note |
| --- | --- |
| 2 | interval started; id captured |
| 3 | cancel clears once and nulls; second call is a no-op: idempotent |
| 2 | no `.unref()`: the interval keeps a Node process alive until cancelled; the requirement does not mention process exit (note, not finding) |
| 1 | `fn` that throws inside the interval: an uncaught exception in a timer callback crashes Node; the requirement does not say to handle it (note) |

**Findings**

- None against the requirement.

**Confidence 5 · Approve.**

# Scoring yourself

| Block | Verdict | The one thing |
| --- | --- | --- |
| 1 | request changes | a throwing task strands the queue |
| 2 | request one change | `<` vs `<=` for stability |
| 3 | approve | |
| 4 | approve | the `as any` is contained |
| 5 | request changes | timed-out waiter eats a permit |
| 6 | request one change | `"constructor"` as id |
| 7 | approve | |
| 8 | approve with note | shared `Response` body |
| 9 | approve | |
| 10 | approve | |

Five approvals, four single-defect blocks, one note. If your count differs by more than one in either direction, redo the mismatched blocks with the card, out loud.
