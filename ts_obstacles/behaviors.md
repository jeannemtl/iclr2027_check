---
title: "Eight Runtime Behaviors"
subtitle: "What the TypeScript runtime does that the syntax does not show — one model, one example, one review question each"
date: "October 2026"
---

**Why this sheet.** A "behavior" is a rule the runtime follows that you cannot see on the line itself. Promises are the biggest (they have their own sheet). These are the other seven, plus one more on equality. Each has: the one-line model to hold in your head, a concrete example with the value you end up holding, and the review question it raises.

# 1. Reference behavior

**Model.** A variable is a label. Objects, arrays, `Map`, `Set`, class instances are shared by label; numbers, strings, booleans, `null`, `undefined` are copied. `const` locks the label, never the contents.

```ts
const a = { n: 1 };  const b = a;  b.n = 2;   // a.n is 2: one object, two labels
let x = 1;           let y = x;    y = 2;     // x is 1: primitives copy
const arr = [3, 1];  arr.sort();              // legal under const: contents changed, label did not
arr = [];                                      // TypeError: label re-pointed
```

Copies are shallow: `[...a]`, `{ ...o }`, `a.slice()`, `new Map(m)` copy one level; nested objects inside are still shared. `structuredClone` is deep. `filter` copies the array, not the objects in it.

**Review question.** For every `push` / `sort` / `splice` / `o.x = v` / `delete`: who else is holding this object? A parameter, a shared module variable, a cached value, a value already returned to a caller.

# 2. Coercion behavior

**Model.** Every operator has a preferred type and bends its operands to get it, silently. Python would raise; TypeScript converts and continues.

| Expression | Converts | Result |
| --- | --- | --- |
| `5 == "5"` | string to number | `true` |
| `0 == ""` | both to number | `true` |
| `"5" * 2` | string to number | `10` |
| `"5" + 2` | number to string | `"52"` |
| `"0" + 1` | number to string | `"01"` (the `for...in` index trap) |
| `Number("abc")` | | `NaN`, no throw |
| `Number("")` | | `0` |
| `Number(null)` | | `0`; `Number(undefined)` is `NaN` |
| `if ([])` | object to boolean | truthy |
| `if ("0")` | string to boolean | truthy |
| `[] + {}` | both to string | `"[object Object]"` |
| `true + 1` | boolean to number | `2` |

The eight falsy values are `false`, `0`, `-0`, `0n`, `""`, `null`, `undefined`, `NaN`; everything else is truthy. `===` never coerces.

**Review question.** For every `==`, `+` with a string nearby, `Number(...)` on input, and `if (x)` on something that can be `0`, `""` or `[]`: what does the conversion produce, and did the author mean it?

# 3. Execution-order behavior (the event loop)

**Model.** One thread. Code runs in this order, every time: (1) the current synchronous task to its end; (2) every queued *microtask* (`await` continuations, `.then` / `.catch` callbacks, `queueMicrotask`); (3) one *macrotask* (`setTimeout`, `setInterval`, I/O completion, a new request); then back to (2).

```ts
console.log(1);
setTimeout(() => console.log(2), 0);          // macrotask: later
Promise.resolve().then(() => console.log(3)); // microtask: after sync, before timers
console.log(4);
// prints 1, 4, 3, 2
```

Consequences:

| Fact | Why it matters |
| --- | --- |
| An `async` function runs synchronously up to its first `await` | the code before the first `await` happens immediately, in the caller's turn |
| Every `await` is a yield point | another request can run between the lines above and below it; that is the read-await-write race |
| `setTimeout(fn, 0)` is never immediate | it runs after every pending microtask; `0` means "next macrotask", not "now" |
| Timer delays are minimums | `setTimeout(fn, 100)` fires at 100 ms or later, never earlier |
| A long synchronous loop blocks everything | no request, timer or `.then` runs until it finishes; `await` inside a hot loop yields |
| `setInterval` keeps the process alive | until `clearInterval` or `.unref()` |
| Two `await`s in a row are sequential | the second starts only when the first settles; `Promise.all` starts both at once |

Five orderings to be able to predict:

```ts
// A                                   // B
await a(); await b();                  await Promise.all([a(), b()]);
// a then b, sequential                // a and b together, wait for both

// C                                   // D
const p = a(); await b(); await p;     ids.forEach(async (id) => await save(id));
// a and b together (a started first)  console.log("x");   // prints before any save finishes

// E
async function f() { console.log("in"); await 0; console.log("after"); }
f(); console.log("out");               // in, out, after
```

**Review question.** For every shared variable: is it read before an `await` and written after? For every pair of independent `await`s: could they be `Promise.all`? For every `setTimeout(fn, 0)`: does the author think it is immediate?

# 4. Scope and `this` behavior

**Model.** `let` and `const` are block-scoped and get a fresh binding per loop iteration; `var` is function-scoped and shared. A closure captures the *variable*, not its value at the time. `this` in a regular function is whatever called it (or `undefined` in modules); an arrow has no `this` of its own and uses the one where it was written.

```ts
for (var i = 0; i < 3; i++) setTimeout(() => console.log(i));   // 3, 3, 3: one shared i
for (let i = 0; i < 3; i++) setTimeout(() => console.log(i));   // 0, 1, 2: one i per iteration

class Btn {
  label = "ok";
  handle() { return this.label; }
}
const b = new Btn();
b.handle();                      // "ok": called on b
const h = b.handle; h();         // TypeError: this is undefined; the method was detached
el.on("click", b.handle);        // same bug, in callback form
el.on("click", () => b.handle()); // fixed: arrow calls it on b
el.on("click", b.handle.bind(b)); // fixed: bound
```

Also: a function declared with `function` is hoisted (usable before its line); `const f = () => {}` is not. Variables declared with `let`/`const` cannot be read before their line (temporal dead zone).

**Review question.** For every callback that references a loop variable: `let` or `var`? For every `obj.method` passed without calling it: does it use `this` inside?

# 5. Error-propagation behavior

**Model.** A thrown error unwinds the *synchronous call stack* to the nearest enclosing `try`. An `await` boundary breaks the stack: a rejected Promise re-enters a stack only at the line that `await`s it. `finally` runs on every exit. An error nobody catches crashes Node (unhandled exception or unhandled rejection) or logs in a browser.

```ts
function a() { throw new Error("x"); }
function b() { a(); }
try { b(); } catch (e) { /* caught: a -> b -> here is one synchronous stack */ }

async function c() { throw new Error("y"); }
try { c(); } catch (e) { /* NOT caught: c returned a rejected Promise; the stack ended */ }
try { await c(); } catch (e) { /* caught: the await re-threw it here */ }
```

| Situation | Where the error goes |
| --- | --- |
| `throw` in sync code | nearest enclosing `try` up the call stack |
| `throw` in an `async` function | the returned Promise rejects |
| rejection, awaited inside a `try` | that `try`'s `catch` |
| rejection, never awaited | unhandled rejection; process exits in modern Node |
| `throw` inside a `setTimeout` callback | nobody; the `try` around `setTimeout` ended long ago |
| `throw` inside a `.then` callback | the chain rejects; caught by a later `.catch` or an `await` |
| `throw` inside an Express async handler (v4) | not caught by Express; request hangs unless `next(err)` |
| `JSON.parse` on bad input | throws synchronously, right there |
| `catch (e)` | `e` is `unknown`; narrow with `instanceof Error` |
| `finally` | runs after `return`, `throw`, or normal exit; cleanup goes here |

**Review question.** For every `throw` and every call that can reject: trace up to the `try` that will see it, or say "nobody". For every `catch`: does it swallow, log-and-continue, or re-throw with `cause`?

# 6. Type-erasure behavior

**Model.** Every type annotation, `interface`, `type`, generic, `as`, `!`, `satisfies`, `readonly`, `private` disappears at compile time. Nothing checks at runtime. Types are a contract the compiler enforces among your own files; the boundary with the outside world (HTTP body, headers, query, files, env, `JSON.parse`, databases returning `any`) is untyped and must be validated by hand.

```ts
interface User { id: number; name: string }
const u = JSON.parse('{"id":"42"}') as User;   // compiles; u.id is the STRING "42"; name is undefined
u.name.toUpperCase();                           // TypeError at runtime; the type said it was there

function f(x: number) { return x * 2 }
f("5" as any);                                  // compiles; returns 10 by coercion, not by type
```

| Written | Runtime effect |
| --- | --- |
| `x: number` | none |
| `x as T` | none; pure relabel |
| `x!` | none; pure claim |
| `interface` / `type` | none; erased |
| `readonly`, `private`, `protected` | none; `#field` is the one runtime-private form |
| `enum` | a real object (numeric by default) |
| `class` | a real constructor function |
| `typeof x` in a value position | real; returns a string |
| `instanceof` | real; checks the prototype chain |
| zod / joi / manual `typeof` checks | real; this is how you actually validate |

**Review question.** For every value that crosses the boundary: where is the runtime check, or is a type annotation standing in for one? Every `as`, `!` and `any` is a place the answer can be "nowhere".

# 7. Prototype behavior

**Model.** A plain object `{}` inherits from `Object.prototype`, so it already has keys you did not put there: `constructor`, `toString`, `hasOwnProperty`, `__proto__`. Lookups fall through to the prototype when the own key is missing. `Map` and `Object.create(null)` have no such inheritance.

```ts
const o: Record<string, number[]> = {};
"constructor" in o              // true, inherited
o["constructor"]                // a function, not undefined
o[userKey].push(1)              // if userKey is "constructor": TypeError; if "__proto__": pollutes every object
Object.keys(o)                  // [] : own keys only; the inherited ones are hidden from iteration
for (const k in o) {}           // can include inherited enumerable keys from a modified prototype
```

**Review question.** Is a plain object indexed by a user-controlled key? Then `Map`. Is `k in obj` used where `Object.hasOwn(obj, k)` or `map.has(k)` was meant?

# 8. Equality behavior

**Model.** Objects compare by identity, never by contents. Two separately built objects are never `===`, even with identical fields. Primitives compare by value. `NaN` is not equal to anything, including itself.

```ts
{ a: 1 } === { a: 1 }            // false: two objects
[1, 2] === [1, 2]                // false
new Date(0) === new Date(0)      // false; compare .getTime()
"a" === "a"                      // true: primitives
NaN === NaN                      // false; use Number.isNaN
const x = { a: 1 }; const y = x; x === y   // true: same object
```

| To compare | Use |
| --- | --- |
| two primitives | `===` |
| two dates | `d1.getTime() === d2.getTime()` |
| two arrays by contents | length + every element, or a helper |
| two objects by contents | field by field, `JSON.stringify` both (key-order sensitive), or a deep-equal helper |
| membership of an object in an array | `arr.includes(obj)` is identity; `arr.some((o) => o.id === id)` for contents |
| a `Set` or `Map` keyed by objects | keys are by identity; `set.has({ a: 1 })` is `false` for a fresh literal |
| `NaN` | `Number.isNaN(x)` |

**Review question.** For every `===`, `includes`, `indexOf`, `Set.has`, `Map.get` on an object or date: is the author comparing identity when they meant contents?

# The eight in one table

| # | Behavior | One-line model | First place to look |
| --- | --- | --- | --- |
| 1 | Reference | labels share objects; copies are shallow; `const` locks the label | every mutation |
| 2 | Coercion | operators convert silently; `===` does not | `==`, `+`, `Number()`, `if (x)` |
| 3 | Execution order | sync, then all microtasks, then one macrotask; every `await` yields | shared state around `await`; `setTimeout(fn, 0)` |
| 4 | Scope and `this` | `let` per iteration, `var` shared; `this` is the caller; arrows inherit | `var` in loops; detached methods |
| 5 | Error propagation | unwinds the sync stack; `await` is the only async re-entry | every `throw`, every `catch` |
| 6 | Type erasure | types vanish; the boundary is untyped | `as`, `!`, `any`, `JSON.parse`, `req.body` |
| 7 | Prototype | plain objects have inherited keys | user-controlled keys on `{}` |
| 8 | Equality | objects by identity, primitives by value | `===`, `includes`, `Set.has` on objects |
