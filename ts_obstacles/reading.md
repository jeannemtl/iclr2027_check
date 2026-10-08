---
title: "Reading TypeScript: Functions, Async, Symbols"
subtitle: "Three decoders for code you have never seen — every statement with how to say it out loud"
date: "October 2026"
---

**How to use the "Read aloud" column.** It is the sentence you say in your head (or on the Loom) when you meet that line. Say it exactly; if the sentence does not fit the line you are looking at, the line is doing something else and you have found a place to slow down.

# 1. Reading a function

**The shape**

```ts
export async function getUser(id: string, retries = 3, opts?: Opts): Promise<User | null> {
^^^^^^ ^^^^^ ^^^^^^^^ ^^^^^^^ ^^^^^^^^^^  ^^^^^^^^^^^  ^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^
export async keyword  name    required    default      optional      return type (Promise: async)
```

Read aloud: *"Exported async function `getUser` that takes a required string `id`, a number `retries` defaulting to 3, and an optional `opts`, and promises to return a `User` or `null`."*

Then, in this order: find every `return` in the body and ask whether each one matches that promise.

**Every function shape**

| Written | Read aloud | What to check |
| --- | --- | --- |
| `function f(x: number): string { ... }` | "function `f` takes a number `x`, returns a string" | every path returns a string? |
| `const f = (x: number): string => { ... }` | "`f` is an arrow function: takes a number `x`, returns a string, body in braces" | braces need an explicit `return` |
| `const f = (x: number) => x * 2` | "`f` is an arrow: takes `x`, returns `x` times 2" | no braces, so the expression IS the return |
| `const f = function (x: number) { ... }` | "`f` is a function expression taking `x`" | old style; `this` depends on caller |
| `async function f(): Promise<T>` | "async function `f`, returns a promise of `T`" | callers must `await` it |
| `const f = async (x) => { ... }` | "`f` is an async arrow taking `x`" | returns a Promise whatever the body returns |
| `f(x: number) { ... }` inside `class` | "method `f` on the class, takes `x`" | `this` is the instance only when called as `obj.f()` |
| `static f() { ... }` | "static method `f`, called on the class itself" | `A.f()`, not `new A().f()` |
| `get total() { ... }` | "getter `total`: computed when you read `obj.total`" | no parentheses at the call site |
| `function f<T>(x: T): T` | "generic `f`: takes some type `T`, returns the same `T`" | `T` is a placeholder; skip it |
| `function f(x: unknown): x is Id` | "type guard: returns true if `x` is an `Id`, and tells the compiler so" | is the body's check actually correct? |
| `function f(msg: string): never` | "`f` never returns normally" | must throw or loop |
| `function f(): void` | "`f` returns nothing useful" | a `return value` here is a type error |
| `(x: number) => string` in a TYPE position | "a function type: number in, string out" | describes a callback parameter, not a function body |
| `arr.map((x) => ...)` | "map over `arr`, calling this arrow once per element" | the arrow is an argument, not a declaration |
| `function f(a: string): void; function f(a: number): void; function f(a: any) {}` | "two overload signatures, then one implementation" | the last one is the real body |

**Parameters**

| Written | Read aloud | Inside the body |
| --- | --- | --- |
| `x: number` | "required number `x`" | `x` is a number |
| `x?: number` | "optional `x`, number if present" | `x` is `number \| undefined`; check before use |
| `x = 5` | "`x` defaults to 5 when not passed" | default applies only for `undefined`, not `null` |
| `x: number = 5` | "number `x`, default 5" | same |
| `...rest: number[]` | "collect any further arguments into the array `rest`" | `rest` is always an array, possibly empty |
| `{ a, b }: Opts` | "destructure the `Opts` argument into locals `a` and `b`" | caller passes one object `{ a: 1, b: 2 }` |
| `{ a = 1, b }: Opts = {}` | "destructure `Opts`, `a` defaults to 1, and the whole argument defaults to an empty object" | caller may pass nothing at all |
| `[x, y]: [number, number]` | "destructure a two-number tuple into `x` and `y`" | |
| `this: Window` as first param | "declares what `this` must be" | not a real argument; callers skip it |

**What does it actually return? Trace every path**

```ts
function find(xs: User[], id: string): User {   // "find takes users and an id, returns a User"
  for (const u of xs) {                         // "for each u in xs"
    if (u.id === id) return u;                  // "if u's id equals id, return u"      <- path 1: a User
  }
                                                // "end of loop; nothing returned"       <- path 2: undefined ✗
}
```

Read aloud: *"Declared to return a `User`, but if no id matches, the function falls off the end and returns `undefined`. The declaration lies to the caller."*

| Pattern | Read aloud | Returns |
| --- | --- | --- |
| no `return` at all | "this function returns nothing" | `undefined` |
| `return;` | "return with no value" | `undefined` |
| `if (c) return a;` with no else | "returns `a` only when `c`; otherwise falls through" | `a` or `undefined` |
| `x => { x * 2 }` | "arrow with a block body and no return" | `undefined` ✗ |
| `x => x * 2` | "arrow that returns `x` times 2" | `x * 2` |
| `async` function with `return 5` | "async, so this resolves to 5 inside a Promise" | `Promise<number>` |
| `async` function that throws | "async, so the throw becomes a rejected Promise" | rejected Promise |
| `return await p` | "wait for `p`, then return its value" | caught by this function's `try` |
| `return p` | "hand the Promise `p` straight back" | NOT caught by this function's `try` |
| `arr.forEach(cb)` | "forEach always returns undefined" | `undefined` |
| `arr.map(x => { x * 2 })` | "map with a block body and no return" | array of `undefined` ✗ |

**Trace one call**

1. Write the arguments: `getUser("42")` → "`id` is the string 42, `retries` is 3, `opts` is undefined."
2. Walk each line saying what it does and what each variable holds afterwards.
3. At each `if`, say which branch your values take, and what the other branch would need.
4. At each `return`, say "returns X, declared Y; match?"
5. Repeat with an edge input: `""`, `undefined`, `0`, an id that does not exist.

**Review questions for any function**

- Does every `return` path match the declared type? (a missing path returns `undefined`)
- Can any parameter be `undefined` where the body assumes it is not?
- Is every `?` or `= default` parameter handled when the caller omits it?
- Does it mutate a parameter (`xs.sort()`, `opts.x = ...`) the caller still uses?
- If `async`: does every caller `await` it?

# 2. Reading an async block

**The annotated example**

```ts
async function load(ids: string[]): Promise<User[]> {
  const cache = getCache();            // 1. "cache is whatever getCache returns, right now" (sync)
  const token = await getToken();      // 2. "WAIT for getToken, then token is its value" (a string)
  const p = fetchUser(ids[0]);         // 3. "p is the PROMISE from fetchUser; the request has started"
  const u = await p;                   // 4. "WAIT for p, then u is the User"

  const all = await Promise.all(       // 5. "start every fetch at once, WAIT for all of them"
    ids.map((id) => fetchUser(id))     //    "map each id to a Promise<User>"
  );                                   //    "all is the array of Users, in input order"

  ids.forEach(async (id) => {          // 6. "for each id, start an async callback"   ✗
    await save(id);                    //    "...which waits for save, but forEach does not wait for it"
  });                                  //    "so load() continues before any save finishes"

  try {
    const r = fetchUser("x");          // 7. "r is a Promise, not awaited"   ✗
    return [u, ...all];                //    "a rejection of r escapes this try"
  } catch (e) {                        // 8. "e is unknown"
    throw new Error("load failed", { cause: e });   // "wrap and rethrow, keeping the cause"
  }
}
```

**Promise or value? Decide for every line**

| Line looks like | Read aloud | Is this a bug? |
| --- | --- | --- |
| `const x = await f()` | "wait for `f`, `x` is its value" | ✓ |
| `const x = f()` where `f` is async | "`x` is the Promise from `f`, not the value" | ✗ unless awaited later or passed to `Promise.all` |
| `const x = f().then(g)` | "`x` is a Promise of `g` applied to `f`'s result" | ✓ if awaited or returned |
| `return f()` inside async | "hand `f`'s Promise back to my caller" | ✓, but not caught by this function's `try` |
| `return await f()` | "wait for `f`, then return the value" | ✓, and caught by this function's `try` |
| `f();` alone, `f` async | "start `f` and walk away" | ✗ unless `.catch` is attached or intended |
| `await f(); await g();` | "wait for `f`, then wait for `g`" (sequential) | ✓ if `g` needs `f`'s result; slow if independent |
| `await Promise.all([f(), g()])` | "start `f` and `g` together, wait for both, results in order" | ✓; rejects on the FIRST failure |
| `await Promise.allSettled([...])` | "start all, wait for all, report each as fulfilled or rejected" | ✓ when partial failure is acceptable |
| `arr.map(async x => ...)` | "map each `x` to a Promise" | ✗ until wrapped in `Promise.all` |
| `arr.forEach(async x => ...)` | "start a callback per `x` and do not wait for any" | ✗ almost always |
| `for (const x of arr) await f(x)` | "for each `x`, wait for `f` before the next" | ✓ if order matters; otherwise slow |
| `await` inside a non-async function | "syntax error" | |
| `res.json()` | "a Promise of the parsed body" | ✗ if used without `await` |
| `JSON.parse(s)` | "parse `s` now, synchronously" | throws on bad input; needs `try` |

**Where does an error go?**

| Situation | Read aloud | Where the error lands |
| --- | --- | --- |
| `throw` inside an async function | "the Promise this function returned rejects" | caller's `await` |
| `await p` where `p` rejects | "the rejection is thrown right here at the await" | enclosing `try` |
| `p` not awaited, rejects | "nobody is listening" | unhandled rejection; crashes Node |
| `try { f() } catch {}` with async `f` | "the try finishes before `f`'s Promise settles" | NOT caught |
| `try { await f() } catch {}` | "the try waits, so a rejection is thrown inside it" | caught |
| `try { return f() } catch {}` | "the Promise leaves the try unresolved" | NOT caught |
| `try { return await f() } catch {}` | "waits inside the try" | caught |
| `Promise.all` with one rejection | "the first failure rejects the whole thing; the rest are ignored" | enclosing `try` |
| `.catch(() => {})` | "swallow the error silently" | nowhere; a finding unless intended |
| `catch (e) { e.message }` | "`e` is unknown; `.message` is a type error" | needs `instanceof Error` |

**Shared state across an `await`**

Every `await` is a point where another request can run. Read aloud for any shared variable: *"read before the await, write after the await: someone else can run in between."*

```ts
const n = counter.get(k) ?? 0;    // "read n"
await db.save(...);               // "WAIT; another request may read the same n here"
counter.set(k, n + 1);            // "write n plus 1; the other request's increment is lost"
```

Cache version: `if (!cache.has(k)) cache.set(k, await load(k))` reads *"if not cached, wait for load, then store"*; every concurrent miss passes the `if` before any store happens. Fix: store the Promise, `cache.set(k, load(k))`, then `await cache.get(k)`.

**Timers**

| Written | Read aloud | Trap |
| --- | --- | --- |
| `setTimeout(fn, ms)` | "run `fn` once, after `ms` milliseconds" | `clearTimeout(id)` cancels |
| `setInterval(fn, ms)` | "run `fn` every `ms` milliseconds, forever" | never cleared = leak; `.unref()` lets Node exit |
| `await new Promise(r => setTimeout(r, ms))` | "sleep for `ms`" | the Python `await asyncio.sleep` |
| `setTimeout(fn, 0)` | "run `fn` after everything pending" | still after every `.then` |
| `Date.now()` | "milliseconds since 1970, as a number" | hard-coded = untestable; inject a clock |

**Review questions for any async block**

- For each line: Promise or value? Is every Promise awaited, returned, or passed to `Promise.all`?
- Is there an `async` callback inside `forEach`?
- Is there a `try` whose body has an un-awaited call?
- Independent awaits in sequence that could be parallel?
- Shared state read before an `await` and written after?
- `res.ok` checked before `res.json()`?
- Interval cleared or `.unref()`'d?

# 3. Symbol decoder

The same character means different things by position. Find the position first, then say the sentence.

**`?`**

| Position | Read aloud | Example |
| --- | --- | --- |
| after a property name in a type | "`a`, optional" | `{ a?: number }` |
| after a parameter name | "`x`, optional" | `f(x?: string)` |
| between two expressions, with a `:` later | "if ... then ... else ..." | `ok ? a : b` |
| before `.`, `[` or `(` | "`o`, if it exists, dot `a`" | `o?.a`, `arr?.[0]`, `cb?.()` |
| `??` | "`x`, or if missing, 10" | `x ?? 10` |
| `??=` | "set `x` to 10 if it is missing" | `x ??= 10` |

**`!`**

| Position | Read aloud | Example |
| --- | --- | --- |
| before an expression | "not `x`" | `!x`, `!arr.length` |
| after an expression | "`user`, which I promise is not null" (compile-time only) | `user!.name` |
| `!==` | "is not strictly equal to" | `a !== b` |
| `!=` | "is not loosely equal to" (flag it) | `a != b` |

**`:`**

| Position | Read aloud | Example |
| --- | --- | --- |
| after a name in a declaration or parameter | "`x`, of type number" | `x: number` |
| after `)` of a function | "returns a string" | `f(): string` |
| inside `{}` in a VALUE | "key `a` holds 1" | `{ a: 1 }` |
| inside `{}` in a TYPE | "key `a` is a number" | `{ a: number }` |
| in destructuring | "take `a` out and call it `x`" | `const { a: x } = o` |
| second part of a ternary | "else" | `c ? a : b` |
| after `case` | "in the case of" | `case "x":` |

**`=`, `==`, `===`, `=>`**

| Written | Read aloud |
| --- | --- |
| `=` | "set ... to ..." (never "equals") |
| `==` | "loosely equals, after converting" (flag) |
| `===` | "strictly equals" |
| `=>` | "returns" / "maps to" |
| `>=`, `<=` | "at least" / "at most"; check the boundary value |
| `+=`, `-=`, `*=` | "add to", "subtract from", "multiply by" |
| `\|\|=`, `&&=`, `??=` | "set if falsy", "set if truthy", "set if missing" |

**`.` and `...`**

| Written | Read aloud | Example |
| --- | --- | --- |
| `.` | "dot": property or method; chains left to right | `a.b.c()`, `arr.map(f).filter(g)` |
| `?.` | "if it exists, dot" | `a?.b` |
| `...x` in `[ ]` or `{ }` | "spread `x` in here" | `[...a, 1]`, `{ ...o, k: v }` |
| `...x` in a parameter list | "collect the rest into `x`" | `(a, ...rest)` |
| `...x` in destructuring | "and everything else into `x`" | `const { a, ...rest } = o` |

**Brackets**

| Written | Read aloud | Example |
| --- | --- | --- |
| `{ }` in a value | "an object with ..." | `{ a: 1 }` |
| `{ }` after `=>`, `if`, `for`, `function` | "a block of statements" | `() => { return 1 }` |
| `{ }` in a type | "an object shape with ..." | `{ a: number }` |
| `{ }` in `import` | "the named export ..." | `import { x } from "m"` |
| `{ }` in destructuring | "pull out keys ..." | `const { a } = o` |
| `[ ]` in a value | "an array of ..." | `[1, 2]` |
| `[ ]` after a name | "element at" / "key" | `arr[0]`, `obj["k"]` |
| `[ ]` after a type | "array of" | `number[]` |
| `[ ]` in a type with commas | "a tuple of" | `[string, number]` |
| `[ ]` in destructuring | "pull out elements ..." | `const [a, b] = arr` |
| `[k]: v` in an object literal | "key computed from `k`" | `{ [name]: 1 }` |
| `( )` after a name | "call" | `f(x)` |
| `( )` around params | "taking ..." | `(a, b) => ...` |
| `( )` around `{ }` after `=>` | "returns an object" | `() => ({ a: 1 })` |
| `< >` after a name | "of" | `Map<string, number>` = "a Map of string to number" |
| `< >` before `(` in a declaration | "generic over `T`" | `function f<T>(x: T)` |
| `` ` ` `` | "a template string" | `` `Hello ${name}` `` |
| `${ }` inside backticks | "insert the value of" | `` `${a + b}` `` |

**`|`, `&`, `||`, `&&`**

| Written | Where | Read aloud |
| --- | --- | --- |
| `\|` | in a type | "or" |
| `&` | in a type | "and also" |
| `\|\|` | in a value | "or else" (fallback on falsy) |
| `&&` | in a value | "and then" (`a && b` is `b` if `a` truthy, else `a`) |
| `\|`, `&`, `^`, `~`, `<<`, `>>` | with numbers | bitwise; rare; read as integer math |

**Keywords that look like operators**

| Written | Read aloud | Runtime effect |
| --- | --- | --- |
| `x as T` | "`x`, which I claim is a `T`" | none |
| `as const` | "freeze these literals as their exact types" | none |
| `satisfies T` | "check this matches `T`, keep its own type" | none |
| `typeof x` in a value | "the type name of `x`, as a string" | yes |
| `typeof x` in a type | "the type of `x`" | none |
| `x instanceof C` | "was `x` built by class `C`" | yes |
| `"k" in obj` | "does `obj` have key `k`" | yes |
| `for (k in obj)` | "for each key `k` in `obj`" | yes |
| `for (x of arr)` | "for each value `x` of `arr`" | yes |
| `keyof T` | "the names of `T`'s keys" | none |
| `new C()` | "build a new `C`" | yes |
| `await p` | "wait for `p` and unwrap it" | yes |
| `delete o.k` | "remove key `k` from `o`" | yes |
| `void expr` | "run `expr`, give back undefined" | yes |
| `declare` | "this exists somewhere else" | none |
| `readonly` | "cannot be reassigned" (type only) | none |
| `#x` | "private field `x`, enforced at runtime" | yes |
| `@decorator` | "wrap the next thing with `decorator`" | yes |

**Three-second decode**

1. Type or value? After a `:` in a declaration, or inside `interface`/`type`, it is a type and runs nothing. Say "of type ..." for it.
2. Find `=`: say "set [left] to [right]".
3. Find `=>`: say "[params] returns [right]".
4. Find `await`: say "wait for ..."; a Promise-returning call with no `await` is where to look for the bug.
5. Find `?`, `!`, `as`: say "the author claims ..." and ask whether the claim holds at runtime.
