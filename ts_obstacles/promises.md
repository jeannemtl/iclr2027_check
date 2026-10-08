---
title: "Is It a Promise?"
subtitle: "How to tell, from the declaration, the body, or the caller — and the full list of things that return one"
date: "October 2026"
---

**The one question.** For every function call you read: *ticket or value?* A Promise is a ticket for a value that arrives later; `await` cashes it. Holding a ticket and treating it as the value is the single most common planted bug.

# What makes a function return a Promise (the facts)

Exactly two things. No annotation is required for the Promise to exist.

| Fact | Example | Result |
| --- | --- | --- |
| The `async` keyword | `async function f() { return 5 }` | `Promise<number>`, always, even if the body is instant |
| The body returns something that is already a Promise | `function f() { return fetch(url) }` | `Promise<Response>`, passed through |

The `: Promise<T>` annotation does not make a function return a Promise; it only documents that one of the two facts holds. It is optional and frequently omitted.

# How to tell (the clues, in order of reliability)

| # | Clue | Where you look | Example |
| --- | --- | --- | --- |
| 1 | `async` keyword | the declaration | `async function getUser(...)`, `const f = async () =>` |
| 2 | `: Promise<T>` return type | the declaration, after `)` | `function getUser(id): Promise<User>` |
| 3 | the body returns a Promise-maker | the `return` statements | `return fetch(...)`, `return db.query(...)` |
| 4 | callers `await` it | every call site | `const u = await getUser(id)`, `.then(...)`, inside `Promise.all` |
| 5 | the name and the job | weakest; a hint only | fetch / load / save / query / read / write / send / connect → usually async |

One clue is enough. Clue 1 is certain. Clue 2 is certain when present. Clue 3 needs you to chase the `return`. Clue 4 is the author telling you. Clue 5 only tells you where to look.

**Say, when you cannot tell:** *"Assuming `getUser` is async, as the `await` on line 12 suggests; if it is synchronous, line 20's `await` is harmless but line 31's missing one is not."* An honest conditional beats a wrong certainty.

# Clue 3 in detail: the pass-through

```ts
function getUser(id: string) {
  return fetch(`/users/${id}`);
}
```

No `async`, no annotation, still a Promise. Say: *"`getUser` returns whatever `fetch` returns."* Then: *"`fetch` returns `Promise<Response>`."* So `getUser` returns `Promise<Response>`. The function is a pipe: whatever goes into the `return` comes out of the call.

**`return X` means the function returns the type of `X`.**

| Body | `X` is | Function returns |
| --- | --- | --- |
| `return 5` | a number | `number` |
| `return fetch(url)` | `Promise<Response>` | `Promise<Response>` |
| `return db.query(sql)` | `Promise<Row[]>` | `Promise<Row[]>` |
| `return getUser(id)` | whatever `getUser` returns | the same; chase one more step |
| `return fetch(url).then(r => r.json())` | a Promise (`.then` always gives one) | `Promise<any>` |
| `return new Promise(...)` | a Promise | a Promise |
| `return items.map(f)` | an array | an array, not a Promise |
| `return await fetch(url)` | the unwrapped Response (needs `async`) | `Promise<Response>` because of `async` |

The chase: follow `return` until you hit an `async` keyword, a known Promise-maker from the list below, or a plain value. Stop there.

**Why authors write it:** `async function f() { return await fetch(...) }` and `function f() { return fetch(...) }` do the same job; the second is shorter. It is a legitimate style, not a finding.

**The one trap in that style:**

```ts
function getUser(id: string) {
  try {
    return fetch(`/users/${id}`);    // the Promise leaves the try before it settles
  } catch (e) {
    log(e);                          // never runs for a network failure
  }
}
```

A rejection escapes the `try` because nothing waited inside it. This is the one place `async` + `return await` genuinely matters.

**The corrections.** Two, depending on whether `getUser` should handle the error itself or hand it to the caller.

*Fix A, catch it here: make the function `async` and `await` inside the `try`.*

```ts
async function getUser(id: string) {
  try {
    return await fetch(`/users/${id}`);   // waits INSIDE the try; a rejection is thrown right here
  } catch (e) {
    log(e);                               // now runs on a network failure
    throw e;                              // re-throw (or return a fallback); never swallow silently
  }
}
```

Three changes: `async` on the function, `await` before `fetch`, and something after `log(e)` so the error is not eaten. `return await` is the one combination where the `await` is not redundant.

*Fix B, do not catch it here: delete the `try` and let the caller handle it.*

```ts
function getUser(id: string) {
  return fetch(`/users/${id}`);           // honest pass-through; nothing to catch here
}

// the caller:
try {
  const res = await getUser("42");        // the await is inside THIS try, so it catches
} catch (e) {
  log(e);
}
```

*Which to recommend:* B when the function has nothing useful to do with the error (pure pass-through); A when it should log, add context, retry, or return a default.

*Say it as:* "Line 3 returns the Promise without `await`, so a rejection escapes the `try` and `log` never runs; either `async` + `return await`, or drop the `try` and let the caller handle it."

*What neither fix covers:* `fetch` resolves on a 404 or 500, so the `catch` only sees network failures. If the requirement is "handle a missing user", add `if (!res.ok) throw new Error(...)` after the `await`, inside the `try`:

```ts
async function getUser(id: string) {
  try {
    const res = await fetch(`/users/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);   // 404/500 become errors too
    return res;
  } catch (e) {
    log(e);
    throw e;
  }
}
```

# Everything that returns a Promise

Memorize these so the chase can stop when it reaches one.

**Language and standard library**

| Call | Returns | Notes |
| --- | --- | --- |
| any function marked `async` | `Promise<whatever it returns>` | the keyword is the proof |
| `new Promise((resolve, reject) => ...)` | `Promise<T>` | the raw constructor |
| `Promise.resolve(v)` | `Promise<T>` | a settled ticket |
| `Promise.reject(e)` | rejected `Promise` | |
| `Promise.all([...])` | `Promise<T[]>` | rejects on first failure |
| `Promise.allSettled([...])` | `Promise<{status, value \| reason}[]>` | never rejects |
| `Promise.race([...])` | `Promise<T>` | first to settle |
| `Promise.any([...])` | `Promise<T>` | first to fulfil |
| `p.then(f)` | `Promise<result of f>` | chaining always yields a Promise |
| `p.catch(f)` | `Promise` | same |
| `p.finally(f)` | `Promise` | same |
| `fetch(url, opts?)` | `Promise<Response>` | resolves on ANY HTTP status; rejects only on network failure |
| `res.json()` | `Promise<any>` | the body, parsed |
| `res.text()` | `Promise<string>` | |
| `res.blob()`, `res.arrayBuffer()`, `res.formData()` | `Promise<...>` | |
| `import("./m")` | `Promise<Module>` | dynamic import |
| `crypto.subtle.*` | `Promise` | Web Crypto |
| `navigator.clipboard.readText()` / `writeText()` | `Promise` | browser |
| `structuredClone` | a value, NOT a Promise | listed to prevent the mistake |
| `JSON.parse`, `JSON.stringify` | a value, NOT a Promise | synchronous; throw/return at once |
| `setTimeout(fn, ms)` | a timer id, NOT a Promise | becomes one only when wrapped: `new Promise(r => setTimeout(r, ms))` |

**Node built-ins**

| Call | Returns | Notes |
| --- | --- | --- |
| `fs.promises.readFile`, `writeFile`, `readdir`, `stat`, `mkdir`, `unlink`, `access` | `Promise` | `import { readFile } from "fs/promises"` |
| `fs.readFileSync` and every `*Sync` | a value | synchronous; blocks |
| `fs.readFile(path, cb)` | `undefined` | callback style, not a Promise; wrap with `util.promisify` |
| `util.promisify(fn)` | a function that returns a Promise | |
| `stream/promises` `pipeline`, `finished` | `Promise` | |
| `timers/promises` `setTimeout(ms)` | `Promise` | the promisified sleep |
| `child_process` `exec` via `promisify` | `Promise` | plain `exec` is callback style |
| `dns.promises.*` | `Promise` | |
| `events.once(emitter, "name")` | `Promise` | |
| `http.request` | a request object, NOT a Promise | event-based |

**Database and HTTP clients (every one of these)**

| Library | Returns a Promise from |
| --- | --- |
| `pg` | `client.query(...)`, `pool.query(...)`, `pool.connect()` |
| `mysql2/promise` | `conn.query(...)`, `conn.execute(...)` |
| `prisma` | `prisma.user.findMany()`, `.findUnique()`, `.create()`, `.update()`, `.delete()`, `$transaction` |
| `mongoose` / `mongodb` | `Model.find()`, `.findOne()`, `.save()`, `collection.insertOne()`, `.updateOne()` |
| `knex` | every query builder chain once awaited; `.then`-able |
| `typeorm` / `sequelize` / `drizzle` | repository and model methods |
| `ioredis` / `redis` | `client.get()`, `.set()`, `.del()`, `.incr()`, `.expire()` |
| `axios` | `axios.get()`, `.post()`, `axios(config)` → `Promise<AxiosResponse>` |
| `node-fetch`, `undici`, `got`, `ky` | same shape as `fetch` |
| `@aws-sdk/*` v3 | `client.send(command)` |
| `firebase` / `firestore` | `getDoc()`, `setDoc()`, `addDoc()`, `getDocs()` |
| `stripe`, `twilio`, `sendgrid`, any SDK | nearly every method |

**Frameworks**

| Context | Promise? |
| --- | --- |
| Express `app.get("/", async (req, res) => ...)` | the handler returns a Promise; Express 4 ignores it, so errors thrown inside are NOT caught without `next(err)` or a wrapper |
| Express `res.json()`, `res.send()`, `res.status()` | NOT Promises; synchronous, chainable; and they do not stop the function |
| Next.js `getServerSideProps`, route handlers, server actions | `async`; return Promises |
| Jest/Vitest `it("...", async () => ...)` | the test runner awaits it |
| React `useEffect(async () => ...)` | ✗ not allowed; `useEffect` expects a sync function or a cleanup; wrap an async call inside |
| Event handlers `onClick={async () => ...}` | allowed; the Promise is ignored, so add `.catch` |

**Your own code**

| Shape | Promise? |
| --- | --- |
| `async function f() {}` | yes |
| `const f = async () => {}` | yes |
| `class A { async m() {} }` | yes |
| `function f() { return fetch(...) }` | yes, pass-through |
| `function f() { return someAsyncFn() }` | yes, pass-through |
| `function f() { someAsyncFn() }` with no `return` | NO: returns `undefined`; the Promise is dropped (fire-and-forget bug) |
| `function f() { return [1, 2].map(x => x) }` | no |
| `function f(): Promise<void> { ... }` without `async` | must return a Promise in the body or it will not compile |

# Things that look async and are not

| Looks like | Actually |
| --- | --- |
| `JSON.parse(s)` | synchronous; throws immediately on bad input |
| `arr.map(async x => ...)` | `map` itself is synchronous and returns `Promise[]`; the Promises are inside the array |
| `arr.forEach(async x => ...)` | `forEach` is synchronous and returns `undefined`; the Promises are thrown away |
| `setTimeout(fn, 0)` | schedules; returns an id; not awaitable |
| `localStorage.getItem` | synchronous |
| `fs.readFileSync` | synchronous |
| `res.json(data)` in Express | synchronous send; nothing to await |
| `console.log` | synchronous |
| `Date.now()` | synchronous |
| `crypto.randomUUID()` | synchronous (`crypto.subtle.*` is async) |

# Decision procedure for any call `g(...)`

1. Is `g` declared `async`? → Promise. Stop.
2. Does its declaration say `: Promise<...>`? → Promise. Stop.
3. Is `g` on the Promise-makers list above (`fetch`, `db.query`, `.then`, `new Promise`, `fs/promises`, any client SDK)? → Promise. Stop.
4. Open `g`'s body. Find every `return`. Is any returned expression a call that passes steps 1–3? → Promise. Stop.
5. Is `g` awaited or `.then`'d anywhere else in the file? → the author thinks it is a Promise; treat it as one and verify with 1–4.
6. None of the above → a plain value.

Then, for every call site of `g`: if it is a Promise, is it `await`ed, `return`ed, `.then`'d, or inside `Promise.all`? If not, that is the finding.

# What the type says once you know

| Written | What you hold after `await` |
| --- | --- |
| `Promise<number>` | a number |
| `Promise<User>` | a User object |
| `Promise<User[]>` | an array of Users |
| `Promise<User \| null>` | a User or null; check before `.name` |
| `Promise<void>` | nothing useful; the point was the side effect |
| `Promise<Response>` | a fetch Response; still need `res.ok` and `await res.json()` |
| `Promise<any>` | anything; checking is off (what `res.json()` gives you) |
| `Promise<unknown>` | anything; must narrow before use |
| `Promise<User>[]` | not awaitable directly; `await Promise.all(...)` first, then `User[]` |
| `Promise<Promise<User>>` | does not exist; Promises flatten; it is just `Promise<User>` |
