---
title: "Reading TypeScript: Functions, Async, Symbols"
subtitle: "Three decoders for code you have never seen — annotated example, then every variation"
date: "October 2026"
---

# 1. Reading a function

**The shape**

```ts
export async function getUser(id: string, retries = 3, opts?: Opts): Promise<User | null> {
^^^^^^ ^^^^^ ^^^^^^^^ ^^^^^^^ ^^^^^^^^^^  ^^^^^^^^^^^  ^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^
export async keyword  name    required    default      optional      return type (a Promise, because async)
  ...
}
```

Find, in this order: the name; the parameters and which are optional; the declared return type; then every `return` statement in the body and ask whether each one matches the declared type.

**Every function shape**

| Written | What it is | Notes |
| --- | --- | --- |
| `function f(x: number): string { ... }` | declaration | hoisted; `this` depends on caller |
| `const f = (x: number): string => { ... }` | arrow assigned to a const | captures surrounding `this`; braces need `return` |
| `const f = (x: number) => x * 2` | arrow, expression body | returns `x * 2` implicitly |
| `const f = function (x: number) { ... }` | function expression | rare in modern code |
| `async function f(): Promise<T>` | async declaration | always returns a Promise, even with `return 5` |
| `const f = async (x) => { ... }` | async arrow | same |
| `f(x: number) { ... }` inside `class` | method | `this` is the instance when called as `obj.f()` |
| `static f() { ... }` | static method | called on the class: `A.f()` |
| `get total() { ... }` | getter | read as `obj.total`, no parentheses |
| `function f<T>(x: T): T` | generic | `T` is a placeholder for whatever is passed |
| `function f(x: string): x is Id` | type guard | returns boolean, narrows `x` for the caller |
| `function f(x: string): never` | never returns | throws or loops forever |
| `function f(): void` | returns nothing useful | a `return value` inside is a type error |
| `(x: number) => string` as a TYPE | function type | describes a callback parameter |
| `arr.map((x) => ...)` | callback | the arrow is handed to `map`, called once per element |
| `function f(a: string): void; function f(a: number): void; function f(a: any) {}` | overloads | the last signature is the implementation |

**Parameters**

| Written | Reads as | Inside the body |
| --- | --- | --- |
| `x: number` | required | `x` is `number` |
| `x?: number` | optional | `x` is `number \| undefined`; check before use |
| `x = 5` | default | `x` is `number`; default applies only when the argument is `undefined`, not `null` |
| `x: number = 5` | default with explicit type | same |
| `...rest: number[]` | collects extra arguments | `rest` is always an array |
| `{ a, b }: Opts` | destructured object parameter | `a` and `b` are locals; the caller passes `{ a: 1, b: 2 }` |
| `{ a = 1, b }: Opts = {}` | destructured with defaults and a default object | caller may pass nothing |
| `[x, y]: [number, number]` | destructured tuple | |
| `this: Window` as first param | declares the type of `this` | not a real argument |

**What does it actually return? Trace every path**

```ts
function find(xs: User[], id: string): User {   // declares: always a User
  for (const u of xs) {
    if (u.id === id) return u;                  // path 1: a User   ✓
  }
                                                // path 2: falls off the end → undefined  ✗ lies to the caller
}
```

| Pattern | Returns |
| --- | --- |
| no `return` at all | `undefined` |
| `return;` | `undefined` |
| `if (...) return a;` with no else | `a` on that branch, `undefined` on the other |
| arrow with braces and no `return` | `undefined` |
| arrow with expression body | that expression |
| `async` function returning `5` | `Promise<number>`, resolves to 5 |
| `async` function that throws | a rejected Promise, not a thrown error |
| `return await p` vs `return p` | same value; only `return await` is caught by a `try` in this function |
| `forEach(cb)` | always `undefined`, whatever `cb` returns |
| `arr.map(x => { x * 2 })` | array of `undefined` (braces, no return) |

**Calling it: trace one call**

1. Write down the arguments: `getUser("42")` → `id = "42"`, `retries = 3`, `opts = undefined`.
2. Walk the body line by line with those values; write what each variable holds after the line.
3. At each `if`, decide which branch with your values, and also note what the *other* branch would need.
4. At each `return`, compare the value with the declared type.
5. Repeat with an edge input: `""`, `undefined`, `0`, an id that does not exist.

**Review questions for any function**

- Does every `return` path match the declared return type? (missing path = `undefined`)
- Can any parameter be `undefined` where the body assumes it is not?
- Is every parameter with a `?` or a `= default` handled when the caller omits it?
- Does it mutate a parameter (`xs.sort()`, `opts.x = ...`) that the caller still uses?
- If `async`: is every call to it awaited by its callers?

# 2. Reading an async block

**The annotated example**

```ts
async function load(ids: string[]): Promise<User[]> {
  const cache = getCache();                     // 1. sync; value right away
  const token = await getToken();               // 2. WAITS here; token is a string, not a Promise
  const p = fetchUser(ids[0]);                  // 3. NO await: p is a Promise<User>, request started
  const u = await p;                            // 4. now waits; u is a User

  const all = await Promise.all(                // 5. starts every fetch at once, waits for all
    ids.map((id) => fetchUser(id))              //    the map returns Promise<User>[]
  );                                            //    all is User[]

  ids.forEach(async (id) => {                   // 6. ✗ forEach ignores the returned Promise;
    await save(id);                             //    these run, but load() does not wait for them
  });

  try {
    const r = fetchUser("x");                   // 7. ✗ not awaited: a rejection escapes this try
    return [u, ...all];
  } catch (e) {                                 // 8. e is unknown; narrow before e.message
    throw new Error("load failed", { cause: e });
  }
}
```

**Promise or value? Decide for every line**

| Line looks like | The variable holds | Is this a bug? |
| --- | --- | --- |
| `const x = await f()` | the resolved value | ✓ |
| `const x = f()` where `f` is async | a `Promise`; `x.name` is `undefined` | ✗ unless `x` is awaited later or passed to `Promise.all` |
| `const x = f().then(g)` | a Promise of `g`'s result | ✓ if awaited or returned |
| `return f()` inside async | the Promise, flattened for the caller | ✓, but not caught by this function's `try` |
| `return await f()` | same value | ✓, and caught by this function's `try` |
| `f();` alone on a line, `f` async | fire-and-forget | ✗ unless `.catch` is attached or intended |
| `await f(); await g();` | sequential | ✓ if `g` needs `f`'s result; slow if independent |
| `await Promise.all([f(), g()])` | parallel, array of results in order | ✓; rejects on the FIRST failure |
| `await Promise.allSettled([...])` | array of `{status, value \| reason}` | ✓ when partial failure is acceptable |
| `arr.map(async x => ...)` | an array of Promises | ✗ until wrapped in `Promise.all` |
| `arr.forEach(async x => ...)` | nothing; callbacks run detached | ✗ almost always |
| `for (const x of arr) await f(x)` | sequential, one at a time | ✓ if order matters; otherwise slow |
| `await` inside a non-async function | syntax error | |
| `res.json()` | a Promise | ✗ if used without `await` |
| `JSON.parse(s)` | a value (sync) | throws on bad input; needs `try` |

**Where does an error go?**

| Situation | Where the error lands |
| --- | --- |
| `throw` inside an async function | the returned Promise rejects |
| `await p` where `p` rejects | thrown at the `await` line; caught by an enclosing `try` |
| `p` not awaited, rejects | unhandled rejection; crashes Node or logs in browser |
| `try { f() } catch {}` with async `f` | NOT caught; the Promise escapes the `try` |
| `try { await f() } catch {}` | caught |
| `try { return f() } catch {}` | NOT caught |
| `try { return await f() } catch {}` | caught |
| `Promise.all` with one rejection | rejects immediately with that one error; others keep running but are ignored |
| `.catch(() => {})` | swallowed silently; a finding unless intended |
| `catch (e) { e.message }` | type error: `e` is `unknown`; needs `instanceof Error` |

**Shared state across an `await`**

Every `await` is a point where another request can run. Read-then-await-then-write on anything shared (a `Map`, a module-level variable, a counter) is a race.

```ts
const n = counter.get(k) ?? 0;    // read
await db.save(...);               // another request runs here and reads the same n
counter.set(k, n + 1);            // write: one increment lost
```

Cache version: `if (!cache.has(k)) cache.set(k, await load(k))` lets every concurrent miss call `load`. Fix: store the Promise, `cache.set(k, load(k))`, then `await cache.get(k)`.

**Timers**

| Written | Meaning | Trap |
| --- | --- | --- |
| `setTimeout(fn, ms)` | run `fn` once after `ms` | returns an id; `clearTimeout(id)` cancels |
| `setInterval(fn, ms)` | run `fn` every `ms` | never cleared = leak; `.unref()` lets Node exit |
| `await new Promise(r => setTimeout(r, ms))` | sleep | the Python `await asyncio.sleep` |
| `setTimeout(fn, 0)` | run after all pending microtasks | still after every `.then` |
| `Date.now()` | ms since epoch, a number | hard-coded = untestable; inject a clock |

**Review questions for any async block**

- For each line: Promise or value? Is every Promise awaited, returned, or passed to `Promise.all`?
- Is there an `async` callback inside `forEach`?
- Is there a `try` whose body has an un-awaited call?
- Independent awaits in sequence that could be parallel?
- Shared state read before an `await` and written after?
- `res.ok` checked before `res.json()`?
- Interval cleared or `.unref()`'d?

# 3. Symbol decoder

The same character means different things by position. Find the position first, then the meaning.

**`?`**

| Position | Meaning | Example |
| --- | --- | --- |
| after a property name in a type | optional property | `{ a?: number }` |
| after a parameter name | optional parameter | `f(x?: string)` |
| between two expressions with `:` | ternary (if-else) | `ok ? a : b` |
| before `.` or `[` or `(` | optional chaining | `o?.a`, `arr?.[0]`, `cb?.()` |
| `??` | nullish fallback | `x ?? 10` |
| `??=` | assign if nullish | `x ??= 10` |

**`!`**

| Position | Meaning | Example |
| --- | --- | --- |
| before an expression | logical NOT | `!x`, `!arr.length` |
| after an expression | non-null assertion (compile-time only) | `user!.name` |
| `!==` | strict not-equal | `a !== b` |
| `!=` | loose not-equal (flag it) | `a != b` |

**`:`**

| Position | Meaning | Example |
| --- | --- | --- |
| after a name in a declaration or parameter | type annotation | `x: number` |
| after `)` of a function | return type | `f(): string` |
| inside `{}` in a VALUE | object key-value | `{ a: 1 }` |
| inside `{}` in a TYPE | property type | `{ a: number }` |
| in destructuring | rename | `const { a: x } = o` |
| second part of a ternary | else | `c ? a : b` |
| after `case` / label | switch case | `case "x":` |

**`=`, `==`, `===`, `=>`**

| Written | Meaning |
| --- | --- |
| `=` | assignment (never comparison) |
| `==` | loose equality with coercion (flag) |
| `===` | strict equality |
| `=>` | arrow function: "returns" |
| `>=`, `<=` | comparison; check the boundary value |
| `+=`, `-=`, `*=` | compound assignment |
| `||=`, `&&=`, `??=` | assign if falsy / truthy / nullish |

**`.` and `...`**

| Written | Meaning | Example |
| --- | --- | --- |
| `.` | property or method access, chains left to right | `a.b.c()`, `arr.map(f).filter(g)` |
| `?.` | optional access | `a?.b` |
| `...x` in `[ ]` or `{ }` | spread: copy elements/keys in | `[...a, 1]`, `{ ...o, k: v }` |
| `...x` in a parameter list | rest: collect the remaining arguments | `(a, ...rest)` |
| `...x` in destructuring | rest: the remaining keys/elements | `const { a, ...rest } = o` |

**Brackets**

| Written | Meaning | Example |
| --- | --- | --- |
| `{ }` in a value | object literal | `{ a: 1 }` |
| `{ }` after `=>`, `if`, `for`, `function` | block body | `() => { return 1 }` |
| `{ }` in a type | object type | `{ a: number }` |
| `{ }` in `import` | named imports | `import { x } from "m"` |
| `{ }` in destructuring | pull keys out | `const { a } = o` |
| `[ ]` in a value | array literal | `[1, 2]` |
| `[ ]` after a name | index access | `arr[0]`, `obj["k"]` |
| `[ ]` after a type | array of | `number[]` |
| `[ ]` in a type with commas | tuple | `[string, number]` |
| `[ ]` in destructuring | pull elements out | `const [a, b] = arr` |
| `[k]: v` in an object literal | computed key | `{ [name]: 1 }` |
| `( )` after a name | call | `f(x)` |
| `( )` around params | parameter list | `(a, b) => ...` |
| `( )` around `{ }` after `=>` | return an object literal | `() => ({ a: 1 })` |
| `< >` after a name | generic argument | `Map<string, number>`, `Promise<User>` |
| `< >` before `(` in a declaration | generic parameter | `function f<T>(x: T)` |
| `` ` ` `` | template string | `` `Hello ${name}` `` |
| `${ }` inside backticks | interpolation | `` `${a + b}` `` |

**`|`, `&`, `||`, `&&`**

| Written | Where | Meaning |
| --- | --- | --- |
| `\|` | in a type | union: either |
| `&` | in a type | intersection: both |
| `\|\|` | in a value | OR; fallback on falsy |
| `&&` | in a value | AND; `a && b` is `b` if `a` truthy else `a` |
| `\|`, `&`, `^`, `~`, `<<`, `>>` | in a value with numbers | bitwise (rare; if seen, read as integer math) |

**Keywords that look like operators**

| Written | Meaning | Runtime effect |
| --- | --- | --- |
| `as T` | cast | none |
| `as const` | literal types | none |
| `satisfies T` | check without widening | none |
| `typeof x` | runtime type name as a string | yes |
| `typeof x` in a type position | the type of `x` | none |
| `instanceof C` | is `x` built from class `C` | yes |
| `in` | `"k" in obj` key check / `for...in` keys | yes |
| `of` | `for...of` values | yes |
| `keyof T` | union of key names | none |
| `new C()` | construct an instance | yes |
| `await p` | wait and unwrap | yes |
| `yield` | generator step | yes |
| `delete o.k` | remove a key | yes |
| `void expr` | evaluate and return `undefined` | yes |
| `declare` | exists elsewhere | none |
| `readonly` | cannot reassign (type only) | none |
| `#x` | runtime-private class field | yes |
| `@decorator` | wraps a class/method | yes |

**Three-second decode**

1. Is this line a type (after `:` or inside `interface`/`type`) or a value? Types run nothing.
2. Find `=`: left is what is being declared, right is the value.
3. Find `=>`: left is parameters, right is what is returned.
4. Find `await`: the thing after it is a Promise being unwrapped; a Promise-returning call without `await` is the bug to look for.
5. Find `?`, `!`, `as`: each is a place the author claimed something about nullness or type; ask whether the claim is true at runtime.
