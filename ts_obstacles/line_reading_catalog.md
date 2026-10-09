---
title: "Reading One Line: the Catalog"
subtitle: "Every option at every one of the seven questions, each with a concrete example, real values, and what you end up holding"
date: "October 2026"
---

**How to use.** At each question, find the row that matches the line in front of you. Every row has the same four parts: the number, the form, a **concrete example with real values**, and **what happens or what the label holds afterward**. Read the example, say the result out loud, and compare. Where a row shows two results (a safe case and a failing case), both are listed because the contrast is the lesson. Assume `users: User[]`, `orders: Order[]`, `req` is an Express request, and `getUser`, `save`, `load` are `async`.

# Q1. What kind of line is it?

**Declarations (a new label or type comes into existence)**

| # | Form | Concrete example | What it does / what is held |
| --- | --- | --- | --- |
| 1 | `const` with value | `const a = 1;` | `a` holds 1. A later `a = 2;` is a TypeError (label locked) |
| 2 | `let` with value | `let a = 1; a = 2;` | `a` holds 2 afterward; `let` allows re-pointing |
| 3 | `let` without value | `let a;` then `a` | `a` holds `undefined` until assigned. `let a: number;` then reading `a` before any assignment is a compile error |
| 4 | `var` | `if (true) { var a = 1; }` then `a` | `a` is 1 OUTSIDE the block (function-scoped). With `let` it would be a ReferenceError outside. Smell in modern code |
| 5 | destructuring object | `const { a, b } = { a: 1, b: 2 };` | `a` holds 1, `b` holds 2. Two labels created |
| 6 | destructuring with rename | `const { a: x } = { a: 7 };` | `x` holds 7. No label `a` exists; reading `a` is a ReferenceError |
| 7 | destructuring with default | `const { a = 5 } = {};` | `a` holds 5. With `{ a: 0 }` it holds 0; with `{ a: null }` it holds `null` (default only for `undefined`) |
| 8 | destructuring rest | `const { a, ...rest } = { a: 1, b: 2, c: 3 };` | `a` holds 1; `rest` holds a NEW object `{ b: 2, c: 3 }` |
| 9 | destructuring array | `const [x, y] = [10, 20, 30];` | `x` holds 10, `y` holds 20, the 30 is ignored |
| 10 | destructuring array rest | `const [h, ...t] = [1, 2, 3];` | `h` holds 1; `t` holds a NEW array `[2, 3]` |
| 11 | function declaration | `function f(x: number) { return x * 2 }` | `f(3)` is 6. Hoisted: `f(3)` works on a line ABOVE the declaration |
| 12 | async function declaration | `async function f() { return 5 }` | `f()` is a Promise (not 5). `await f()` is 5 |
| 13 | generator | `function* g() { yield 1; yield 2; }` | `g()` is an iterator, not a number. `[...g()]` is `[1, 2]` |
| 14 | class | `class A { x = 1 }` | `new A().x` is 1. `A` is a constructor function; `A()` without `new` is a TypeError |
| 15 | class field | `class A { count = 0 }` and `const p = new A(); const q = new A(); p.count++;` | `p.count` is 1, `q.count` is still 0: each instance has its own field |
| 16 | class method | `class A { n = 5; m() { return this.n } }` and `const a = new A();` | `a.m()` is 5. `const f = a.m; f()` is a TypeError (`this` is `undefined`: method detached) |
| 17 | getter / setter | `class A { get total() { return 7 } }` | `new A().total` is 7. `new A().total()` is a TypeError (7 is not a function) |
| 18 | static member | `class A { static n = 0; static f() { return 1 } }` | `A.n` is 0, `A.f()` is 1. `new A().f` is `undefined` (not on instances) |
| 19 | `interface` | `interface U { id: number }` and `const u: U = { id: "x" };` | compile error on the second line. At runtime the interface does not exist and nothing is checked |
| 20 | `type` alias | `type Id = string \| number;` and `let i: Id = 5; i = true;` | first assignment fine; `i = true` is a compile error. Type vanishes at runtime |
| 21 | `enum` | `enum C { A, B }` | `C.A` is 0, `C.B` is 1, `C[0]` is `"A"`. A real object at runtime |
| 22 | `import` | `import { x } from "./m";` and `import y from "./m";` | `x` is the module's named export `x`; `y` is its default export. Same value, shared with every importer |
| 23 | `export` | `export const a = 1;` and `export default f;` | other files can `import { a }` and `import f`. Visibility only; nothing else changes |
| 24 | `declare` | `declare const g: string;` and `g.length` | compiler trusts that `g` exists. If it does not exist at runtime, `g.length` is a ReferenceError |

**Destructuring, worked (every shape, with the input and what each label holds)**

| Statement | Input | Labels created | What each holds | What to check |
| --- | --- | --- | --- | --- |
| `const { id, name } = user;` | `user = { id: 1, name: "Ann", age: 30 }` | `id`, `name` | `id` = 1, `name` = `"Ann"`; `age` is ignored | Q5: if `name?:` is optional, `name` may be `undefined` |
| `const { id, name } = user;` | `user = { id: 1 }` | `id`, `name` | `id` = 1, `name` = `undefined` | no error on a missing key; the crash comes at the next `name.length` |
| `const { id } = user;` | `user = undefined` | none | THROWS `TypeError` | Q5: can `user` be nothing? (`find` miss, optional arg) |
| `const { a: x, b: y } = o;` | `o = { a: 1, b: 2 }` | `x`, `y` | `x` = 1, `y` = 2; `a`, `b` do not exist as labels | reading `a` later is a ReferenceError |
| `const { a = 5, b = 6 } = o;` | `o = { a: 1 }` | `a`, `b` | `a` = 1, `b` = 6 | default only fires on `undefined` |
| `const { a = 5 } = o;` | `o = { a: null }` | `a` | `null`, NOT 5 | a `null` from JSON or a DB slips past the default |
| `const { a: x = 5 } = o;` | `o = {}` | `x` | 5 | rename and default together: `x` is the label |
| `const { a, ...rest } = o;` | `o = { a: 1, b: 2, c: 3 }` | `a`, `rest` | `a` = 1, `rest` = new `{ b: 2, c: 3 }` | `rest` is shallow: nested objects shared with `o` |
| `const { inner } = o;` | `o = { inner: { x: 1 } }` | `inner` | the SAME object as `o.inner` | Q6: alias; `inner.x = 2` changes `o.inner.x` |
| `const { a: { b } } = o;` | `o = { a: { b: 5 } }` | `b` (not `a`) | 5 | `o = { }` THROWS (reading `b` of `undefined`) |
| `const { length } = "abc";` | a string | `length` | 3 | works on primitives (temporary wrapper) |
| `const [x, y] = arr;` | `arr = [10, 20, 30]` | `x`, `y` | 10, 20 | 30 ignored |
| `const [x, y] = arr;` | `arr = [10]` | `x`, `y` | 10, `undefined` | Q5 on `y` |
| `const [x, y] = arr;` | `arr = []` | `x`, `y` | both `undefined` | empty array is not an error |
| `const [x, , z] = arr;` | `arr = [1, 2, 3]` | `x`, `z` | 1, 3 | the gap skips index 1 |
| `const [h, ...t] = arr;` | `arr = [1, 2, 3]` | `h`, `t` | 1, new `[2, 3]` | `t` is a copy; `arr` untouched |
| `const [h, ...t] = arr;` | `arr = []` | `h`, `t` | `undefined`, `[]` | `h` can be nothing; `t` never is |
| `const [first] = list.filter(p);` | filter keeps 0 items | `first` | `undefined` | the idiom for "first match"; Q5 |
| `const [k, v] = pair;` | `pair = ["a", 1]` | `k`, `v` | `"a"`, 1 | the Python `k, v = pair` |
| `for (const [k, v] of Object.entries(o))` | `o = { a: 1, b: 2 }` | `k`, `v` per pass | pass 1: `"a"`, 1; pass 2: `"b"`, 2 | the Python `d.items()` loop |
| `const [a, b] = [b, a];` | after `a = 1, b = 2` (needs `let`, and a prior `;`) | rebinds `a`, `b` | `a` = 2, `b` = 1 | swap without a temp; a missing semicolon on the previous line breaks it |
| `function f({ id, tags = [] }: Opts) {}` | `f({ id: 1 })` | `id`, `tags` inside `f` | 1, a fresh `[]` | calling `f()` with NO argument THROWS; add `= {}` after the pattern |
| `function f([a, b]: [number, number]) {}` | `f([1, 2])` | `a`, `b` | 1, 2 | wrong-length input gives `undefined`s, not errors |
| `const { data: { items = [] } = {} } = res;` | `res = {}` | `items` | `[]` | nested default on both levels prevents the crash |
| `const { a } = o as Config;` | `o` is really `{}` | `a` | `undefined` | the cast hid it; Q5 |

**The three rules to carry**

1. Missing key or missing element gives `undefined`, never an error.
2. Destructuring `undefined` or `null` itself THROWS; that is the crash to look for.
3. A destructured object-valued label is an ALIAS of the original's inner object; only the top level is new when you use `...rest`.

**Assignments (an existing label re-pointed, or an object mutated)**

| # | Form | Concrete example | What it does / what is held |
| --- | --- | --- | --- |
| 25 | reassignment | `let a = 1; a = 2;` | `a` holds 2. Under `const` this line is a TypeError |
| 26 | compound | `let a = 5; a += 1;` and `let s = "x"; s += "y";` | `a` is 6; `s` is `"xy"`. Each is a reassignment: `a = a + 1` |
| 27 | increment | `let i = 0; const j = i++;` | `j` is 0 (post-increment returns the OLD value), `i` is 1. `++i` would give `j` = 1 |
| 28 | logical assignment | `let a = null; a ??= 5;` and `let b = 0; b \|\|= 5;` and `let c = 1; c &&= 9;` | `a` is 5 (was nullish); `b` is 5 (0 is falsy); `c` is 9 (1 is truthy). With `let d = 0; d ??= 5;` `d` stays 0 |
| 29 | property set | `const o = { k: 1 }; const p = o; o.k = 2;` | `o.k` is 2 AND `p.k` is 2 (same object). Allowed under `const`: the label did not move |
| 30 | bracket set | `const o = {}; o["k"] = 1;` and `const a = [0, 0]; a[1] = "x";` | `o` is `{ k: 1 }`; `a` is `[0, "x"]` |
| 31 | nested set | `const o = { a: { b: 1 } }; const inner = o.a; o.a.b = 2;` | `o.a.b` is 2 AND `inner.b` is 2: `inner` is another label on `o.a` |
| 32 | delete | `const o = { k: 1 }; delete o.k;` | `o` is `{}`; `o.k` is `undefined`. On a `Map` this does nothing; `map.delete(k)` is the call |
| 33 | length set | `const a = [1, 2, 3]; const b = a; a.length = 0;` | `a` is `[]` and so is `b` (same array). Empties every alias |
| 34 | destructuring assignment | `let a = 1, b = 2; [a, b] = [b, a];` | `a` is 2, `b` is 1. The right side builds `[2, 1]` first, then assigns |
| 35 | chained | `let a, b; a = b = 0;` | `b = 0` runs first and evaluates to 0; then `a = 0`. Both hold 0 |

**Expression statements (a bare expression; something runs; the result is dropped unless the call mutates)**

| # | Form | Concrete example | What it does / what is held |
| --- | --- | --- | --- |
| 36 | mutating method call | `const a = [1]; a.push(2);` | `a` is now `[1, 2]`. The return value (2, the new length) is dropped; the mutation is the point |
| 37 | non-mutating method call | `const a = [1, 2]; a.map(x => x * 2);` | a new array `[2, 4]` is built and dropped. `a` is still `[1, 2]`. Dead line |
| 38 | sync side-effect call | `console.log(5);` and `res.json({ ok: true });` | first prints 5 and returns `undefined`; second sends the HTTP response. The effect is the point |
| 39 | async call, no await | `save(x);` | starts `save`, gets a Promise, drops it. The next line runs before `save` finishes; if `save` rejects, unhandled rejection |
| 40 | `await` alone | `await save(x);` | waits for `save`; the resolved value is dropped on purpose |
| 41 | `new` alone | `new Worker("w.js");` | starts the worker; the object is dropped (fine if the constructor's effect is the point) |
| 42 | bare value | `x;` and `a + b;` and `o.k;` | computed and discarded; the line does nothing |
| 43 | `void` expression | `void save(x);` | starts `save`, explicitly discards the Promise. If it rejects, still unhandled |
| 44 | IIFE | `(async () => { await save(x); })();` | runs immediately; the async function's Promise is dropped; errors inside are unhandled unless caught inside |

**Control (changes which line runs next)**

| # | Form | Concrete example | What it does / what is held |
| --- | --- | --- | --- |
| 45 | `if` / `else` | `const x = 0; if (x) { A() } else { B() }` | `B()` runs (0 is falsy). With `x = []` `A()` runs (arrays truthy). With `x = "0"` `A()` runs |
| 46 | ternary | `const s = n > 0 ? "pos" : "neg";` | `n = 5` gives `"pos"`; `n = 0` gives `"neg"`; it is an expression with a value |
| 47 | `switch` | `switch (x) { case 1: a(); case 2: b(); }` | `x = 1` runs `a()` THEN `b()` (no `break`: fall-through). `x = "1"` runs neither (`===`, string is not number 1) |
| 48 | `for` | `for (let i = 0; i <= arr.length; i++) {}` with `arr = ["a", "b"]` | `i` takes 0, 1, 2; `arr[2]` is `undefined`: one past the end (off-by-one, `<=` should be `<`) |
| 49 | `for...of` | `for (const x of [10, 20]) {}` | `x` is 10, then 20 |
| 50 | `for...in` | `for (const k in { a: 1, b: 2 }) {}` and `for (const k in [10, 20]) {}` | first gives `"a"`, `"b"`; second gives `"0"`, `"1"` (strings, not numbers, not the elements) |
| 51 | `while` | `let n = 3; while (n > 0) n--;` | stops with `n` = 0. `while (true) {}` with no `break` never ends |
| 52 | `break` / `continue` | `for (const x of [1, 2, 3]) { if (x === 2) break; log(x); }` | logs 1 only. Inside `[1,2,3].forEach(x => { break; })` it is a SyntaxError |
| 53 | `return` | `function f() { return; }` and `function g() { return 5; }` | `f()` is `undefined`; `g()` is 5. Ends the function immediately |
| 54 | `throw` | `function f() { throw new Error("x"); }` and `try { f(); } catch (e) { e.message }` | the `catch` gets the Error; `e.message` is `"x"`. With no enclosing `try`, the process crashes |
| 55 | `try` / `catch` / `finally` | `try { throw 1 } catch (e) { log(e) } finally { cleanup() }` | `e` is 1; `log(1)` runs; `cleanup()` runs regardless, even after `return` or `throw` |
| 56 | labeled statement | `outer: for (const i of [1,2]) { for (const j of [1,2]) { if (j === 2) break outer; } }` | `break outer` leaves BOTH loops; plain `break` would leave only the inner |
| 57 | `yield` | `function* g() { const x = yield 1; }` and `const it = g();` | `it.next()` is `{ value: 1, done: false }`; the generator pauses at `yield` |

**Type-only (runs nothing; note what the author claims)**

| # | Form | Concrete example | What it does / what is held |
| --- | --- | --- | --- |
| 58 | annotation | `let x: number = 5; x = "a";` | `x = "a"` is a compile error. At runtime, the `: number` does not exist |
| 59 | return type | `function f(): string { return 5; }` | compile error; also a path with no `return` is an error under strict settings |
| 60 | cast | `const n = "5" as unknown as number; n + 1` | compiles; at runtime `n` is still the string `"5"`, and `n + 1` is `"51"`. The cast changed nothing |
| 61 | non-null | `const len = s!.length;` with `s` really `undefined` | compiles; at runtime TypeError. The `!` only silenced the compiler |
| 62 | `satisfies` | `const c = { port: 80 } satisfies Config;` | checks the shape against `Config` without widening: `c.port` stays typed `number`. An extra key is a compile error |
| 63 | generic parameter | `function id<T>(x: T): T { return x }` | `id(5)` returns 5 typed `number`; `id("a")` returns `"a"` typed `string`. `T` is a placeholder |
| 64 | `as const` | `const r = ["a", "b"] as const;` | type becomes `readonly ["a", "b"]`; at runtime it is an ordinary mutable array (`r.push("c")` works if cast away) |
| 65 | `typeof` in a type | `const c = { a: 1 }; let d: typeof c;` | `d` must have the type `{ a: number }`; nothing runs |
| 66 | `keyof` | `type K = keyof { a: 1; b: 2 };` | `K` is `"a" \| "b"` |
| 67 | `@ts-ignore` | `// @ts-ignore` above `x.foo();` | the compiler skips the next line; at runtime `x.foo()` may crash. A finding |

# Q2. Where does the value come from?

**Literals**

| # | Form | Concrete example | What it produces |
| --- | --- | --- | --- |
| 1 | string | `"a"`, `'a'`, `` `a${1}` `` | `"a"`, `"a"`, `"a1"` (all primitives) |
| 2 | number | `42`, `3.5`, `-0`, `1e3`, `0x1f`, `NaN`, `Infinity` | 42, 3.5, -0, 1000, 31, `NaN`, `Infinity` |
| 3 | boolean | `true`, `false` | the two booleans |
| 4 | nullish | `null`, `undefined` | the two "nothing" values |
| 5 | bigint | `10n` and `10n + 1` | `10n` is a bigint; `10n + 1` is a TypeError (cannot mix with number) |
| 6 | object literal | `{}`, `{ a: 1 }`, `const a = 3; ({ a })`, `const k = "x"; ({ [k]: 1 })`, `{ ...o }` | `{}`, `{ a: 1 }`, `{ a: 3 }`, `{ x: 1 }`, a shallow copy of `o`. Each evaluation makes a NEW object |
| 7 | array literal | `[]`, `[1, 2]`, `[...[1], ...[2]]` | `[]`, `[1, 2]`, `[1, 2]`. Each evaluation makes a NEW array |
| 8 | function literal | `const f = (x) => x + 1;` | `f(1)` is 2. The arrow is a function object |
| 9 | regex literal | `"abb".match(/ab+/g)` | `["abb"]`. With no match: `null` |
| 10 | template literal | `` `Hello ${name}` `` with `name = "Ann"` | `"Hello Ann"`. With `name = undefined`: `"Hello undefined"` (no error) |
| 11 | `new` expression | `new Map()`, `new Set([1, 1])`, `new Date(0)`, `new Error("m")`, `new User()` | an empty Map; `Set { 1 }`; the epoch Date; an Error with message `"m"`; a `User` instance. Each a NEW object |

**Calls**

| # | Form | Concrete example | What it produces |
| --- | --- | --- | --- |
| 12 | plain function call | `Math.max(1, 3)` and `f(2)` for `function f(x) { return x * 2 }` | 3; 4 |
| 13 | method call | `[3, 1].sort()` and `" a ".trim()` | `[1, 3]` (mutated the array and returned it); `"a"` (new string) |
| 14 | optional call | `const cb = undefined; cb?.(5)` | `undefined`, no crash. Without `?.`: TypeError |
| 15 | constructor | `new Date(0).getTime()` | 0 |
| 16 | chained calls | `[1, 2, 3].filter(x => x > 1).map(x => x * 2)` | `filter` gives `[2, 3]`, then `map` gives `[4, 6]`. The last call's return is the value |
| 17 | IIFE | `(() => 5)()` | 5 |
| 18 | tagged template | `` sql`select ${id}` `` with `id = 7` | calls `sql(["select ", ""], 7)`; the result is whatever `sql` returns |
| 19 | `await` of a call | `await getUser("1")` | the resolved `User`; a rejection throws here |
| 20 | `.then` chain | `getUser("1").then(u => u.name)` | a Promise of the name, not the name |
| 21 | `Promise.all` | `Promise.all([getUser("1"), getUser("2")])` | a Promise of `[user1, user2]` |
| 22 | `JSON.parse` | `JSON.parse('{"a":1}')` and `JSON.parse("x")` | `{ a: 1 }`; throws `SyntaxError`. The result is typed `any` |
| 23 | `Number(x)` | `Number("12")`, `Number("12px")`, `Number("")`, `Number(null)`, `Number(undefined)` | 12, `NaN`, 0, 0, `NaN` |
| 24 | `parseInt` / `parseFloat` | `parseInt("12px", 10)`, `parseInt("px")`, `parseFloat("1.5.3")` | 12, `NaN`, 1.5 |
| 25 | `Object.keys/values/entries` | `Object.keys({ a: 1, b: 2 })`, `Object.values(...)`, `Object.entries(...)` | `["a","b"]`, `[1,2]`, `[["a",1],["b",2]]` (new arrays) |
| 26 | `Array.from` / `isArray` | `Array.from("ab")` and `Array.isArray([])` | `["a","b"]`; `true` |
| 27 | `structuredClone` | `const o = { a: { b: 1 } }; const c = structuredClone(o);` | `c.a !== o.a`; editing `c.a.b` leaves `o.a.b` alone (deep copy) |
| 28 | `Date.now()` | `Date.now()` | a number of milliseconds, e.g. 1760000000000 |
| 29 | `Math.*` | `Math.max(...[])`, `Math.round(2.5)`, `Math.floor(-1.5)` | `-Infinity`, 3, -2 |

**Property and element reads**

| # | Form | Concrete example | What it produces |
| --- | --- | --- | --- |
| 30 | dot | `const o = { k: 1 }; o.k` and `({}).k` | 1; `undefined` (no error) |
| 31 | bracket, string key | `const name = "k"; o[name]` and `({})["constructor"]` | 1; the inherited `Object` function (not `undefined`) |
| 32 | index | `[10, 20][0]`, `[10, 20][2]`, `[10, 20][-1]` | 10, `undefined`, `undefined` |
| 33 | `arr.at(i)` | `[10, 20].at(-1)` and `[].at(0)` | 20; `undefined` |
| 34 | `.length` | `"abc".length` and `[1, 2].length` | 3; 2 (always a number) |
| 35 | `.size` | `new Map([[1, 2]]).size` and `new Set().size` | 1; 0 |
| 36 | `map.get(k)` | `const m = new Map([["a", 1]]); m.get("a"); m.get("b")` | 1; `undefined` |
| 37 | optional chain | `const o = undefined; o?.k`, `o?.a?.b`, `const arr = null; arr?.[0]` | all `undefined`, no crash |
| 38 | nested | `const o = { a: {} }; o.a.b.c` | `o.a.b` is `undefined`, then `.c` on it throws TypeError |
| 39 | request fields | URL `/users/42?page=2`: `req.params.id`, `req.query.page`, `req.query.zzz` | `"42"` (a string), `"2"` (a string), `undefined`. `req.headers["x-k"]` is a string, a string array, or `undefined` |
| 40 | `this.field` | `class A { items = [1]; get() { return this.items } }` | `new A().get()` is `[1]`. `const g = new A().get; g()` is a TypeError (`this` lost) |
| 41 | `process.env.X` | `process.env.PORT` | `"3000"` (a string) or `undefined` if unset |
| 42 | `localStorage.getItem` | `localStorage.getItem("k")` | the stored string, or `null` if absent |

**Operators**

| # | Form | Concrete example | What it produces |
| --- | --- | --- | --- |
| 43 | arithmetic | `5 + 2`, `"5" + 2`, `"5" - 2`, `1 / 0`, `0 / 0`, `7 % 3`, `2 ** 3` | 7, `"52"`, 3, `Infinity`, `NaN`, 1, 8 |
| 44 | string concatenation | `"a" + 1 + 2` and `1 + 2 + "a"` | `"a12"`; `"3a"` (left to right) |
| 45 | comparison | `3 > 2`, `NaN > 1`, `"10" < "9"`, `"10" < 9` | `true`, `false`, `true` (string compare), `false` (numeric compare) |
| 46 | strict equality | `1 === 1`, `1 === "1"`, `NaN === NaN` | `true`, `false`, `false` |
| 47 | loose equality | `0 == ""`, `null == undefined`, `[] == false` | `true`, `true`, `true` (coerced; flag in review) |
| 48 | `&&` | `0 && "x"`, `5 && "x"`, `user && user.name` | 0 (stops at the first falsy), `"x"`, the name if `user` is set else `user` itself |
| 49 | `\|\|` | `0 \|\| 10`, `"" \|\| "anon"`, `5 \|\| 10` | 10, `"anon"`, 5 |
| 50 | `??` | `0 ?? 10`, `null ?? 10`, `undefined ?? 10`, `"" ?? "anon"` | 0, 10, 10, `""` |
| 51 | NOT | `!0`, `!"a"`, `!![]`, `!!""` | `true`, `false`, `true`, `false` |
| 52 | ternary | `5 > 3 ? "y" : "n"` | `"y"` |
| 53 | spread in a literal | `[...[1, 2], 3]` and `({ ...{ a: 1 }, b: 2 })` | `[1, 2, 3]`; `{ a: 1, b: 2 }` (new containers, shallow) |
| 54 | `typeof` | `typeof 5`, `typeof "a"`, `typeof null`, `typeof undefined`, `typeof []`, `typeof (() => 1)` | `"number"`, `"string"`, `"object"` (wart), `"undefined"`, `"object"`, `"function"` |
| 55 | `instanceof` | `[] instanceof Array`, `new Date() instanceof Date`, `({}) instanceof Array` | `true`, `true`, `false` |
| 56 | `in` | `"a" in { a: 1 }`, `"toString" in {}`, `1 in [5, 6]` | `true`, `true` (inherited), `true` (an index) |
| 57 | `delete` | `const o = { k: 1 }; delete o.k` | `true`; `o` is `{}` |
| 58 | `void` | `void 0` | `undefined` |
| 59 | comma | `(1, 2)` | 2 |
| 60 | assignment as an expression | `let a; (a = 5)` and `let b = 9; if (b = 0) {}` | evaluates to 5 (and `a` is 5); the `if` is false AND `b` is now 0 |
| 61 | bitwise | `5 & 3`, `5 \| 3`, `1 << 3`, `~0` | 1, 7, 8, -1 |

**`await` and destructuring**

| # | Form | Concrete example | What it produces |
| --- | --- | --- | --- |
| 62 | `await p` | `await Promise.resolve(5)` and `await Promise.reject(new Error("x"))` | 5; throws the Error at this line |
| 63 | `await` of a non-Promise | `await 5` | 5, after yielding once to other work |
| 64 | `const { a } = o` | `const { a } = { a: 1 }` | `a` holds 1 |
| 65 | `const [x] = arr` | `const [x] = [9]` | `x` holds 9 |
| 66 | nested pattern | `const { a: { b } } = { a: { b: 1 } }` and `= {}` | `b` holds 1; the second throws TypeError (reading `b` of `undefined`) |
| 67 | `for (const [k, v] of map)` | `for (const [k, v] of new Map([["a", 1]]))` | `k` is `"a"`, `v` is 1 |
| 68 | `for (const [k, v] of Object.entries(o))` | `Object.entries({ a: 1 })` | `k` is `"a"`, `v` is 1 |

# Q3. Primitive or object?

**Primitives (immutable, by value, copied, no keys)**

| # | Type | Concrete examples that produce it | Why that is this type |
| --- | --- | --- | --- |
| 1 | `string` | `"a".toUpperCase()` gives `"A"`; `String(5)` gives `"5"`; `[1, 2].join("-")` gives `"1-2"`; `typeof 5` gives `"number"`; `JSON.stringify({ a: 1 })` gives `'{"a":1}'` | every string method, `typeof`, and `JSON.stringify` return a string |
| 2 | `number` | `"abc".length` is 3; `[1].push(2)` is 2 (the new length); `"a".indexOf("b")` is -1; `Math.max(1, 2)` is 2; `Date.now()` | lengths, indexes, counts, math, and timestamps are numbers |
| 3 | `boolean` | `[1].includes(1)` is `true`; `new Map().has("a")` is `false`; `Array.isArray([])`; `1 < 2`; `delete o.k` | predicates and comparisons |
| 4 | `undefined` | `[].find(x => x)`; `new Map().get("a")`; `[1][5]`; `(() => {})()`; `({}).k`; `null?.k` | a miss, an absent key, or no `return` |
| 5 | `null` | `JSON.parse("null")`; `localStorage.getItem("none")`; `"a".match(/b/)`; `await db.findOne({ id: "none" })`; `let x = null` | deliberately empty, or "not found" from an API |
| 6 | `bigint` | `10n`; `BigInt(5)` | only from the `n` literal or `BigInt()` |
| 7 | `symbol` | `Symbol("id")`; `Symbol.iterator` | unique keys; rare |

**Objects (mutable, by identity, aliased, can have keys)**

| # | Kind | Concrete examples that produce it | Why that is an object |
| --- | --- | --- | --- |
| 8 | plain object | `{ a: 1 }`; `{ ...o }`; `JSON.parse('{"a":1}')`; `Object.fromEntries([["a", 1]])`; `req.body` | a bag of keys |
| 9 | array | `[1, 2].map(x => x)`; `"a,b".split(",")` gives `["a","b"]`; `Object.keys({ a: 1 })`; `Array.from("ab")`; `[3,1].toSorted()` | an ordered list |
| 10 | `Map` / `Set` | `new Map()`; `new Set([1, 1])`; `Map.groupBy(arr, f)` | collections |
| 11 | function | `() => {}`; `obj.method` (named, not called); `f.bind(x)` | functions are objects; `typeof` says `"function"` |
| 12 | Promise | `fetch(url)`; `res.json()`; `(async () => 1)()`; `Promise.all([])`; `f().then(g)` | a ticket object |
| 13 | `Date` | `new Date(0)` | mutable: `d.setFullYear(2000)` changes it |
| 14 | `Error` | `new Error("m")`; the `e` in `catch (e)` (whatever was thrown) | has `.message`, `.stack` |
| 15 | `RegExp` | `/x/g`; `new RegExp("x")` | with `g`, carries `lastIndex` state |
| 16 | class instance | `new User()` | an object whose prototype is `User.prototype` |
| 17 | iterator | `[1].entries()`; `new Map().keys()`; `g()` for a generator | has `.next()` |
| 18 | web objects | `new URL("http://x")`; `new Headers()`; the Response from `await fetch(url)` | built-in classes |
| 19 | binary | `Buffer.from("a")`; `new Uint8Array(2)` | byte arrays |
| 20 | framework objects | `req`, `res`, `new EventEmitter()`, a DB pool | provided by libraries |

# Q4. Ticket or value?

**Returns a Promise (a ticket)**

| # | Form | Concrete example | What you hold |
| --- | --- | --- | --- |
| 1 | declared `async` | `async function f() { return 1 }` then `const v = f();` | `v` is a Promise, not 1. `await v` is 1 |
| 2 | annotated `: Promise<T>` | `function f(): Promise<number> { return Promise.resolve(1) }` then `const v = f();` | a Promise |
| 3 | `fetch` | `const r = fetch("/users/1");` | a Promise of a Response. After `await`, a Response with `status` 404 is still a Response |
| 4 | `res.json()` | `const d = res.json();` then `d.user` | `d` is a Promise; `d.user` is `undefined` |
| 5 | `new Promise` | `const p = new Promise((resolve) => resolve(5));` | `p` is a Promise; `await p` is 5 |
| 6 | `Promise.all` and friends | `const p = Promise.all([f(), g()]);` | one Promise of `[fValue, gValue]` |
| 7 | `.then` / `.catch` / `.finally` | `const p = f().then(x => x * 2);` | a Promise of the doubled value (chaining always yields a Promise) |
| 8 | `import()` | `const m = import("./m.js");` | a Promise of the module |
| 9 | `fs/promises` | `const text = readFile("a.txt", "utf8");` | a Promise of a string (`text.length` is `undefined`) |
| 10 | `util.promisify` | `const read = promisify(fs.readFile); const t = read("a.txt");` | a Promise |
| 11 | database client | `const rows = db.query("select 1");` | a Promise of rows; `rows.length` is `undefined` |
| 12 | HTTP client or SDK | `const r = axios.get(url);` and `const out = client.send(cmd);` | Promises |
| 13 | pass-through `return` | `function f() { return fetch(u); }` then `const v = f();` | `v` is a Promise although `f` has no `async` |
| 14 | `map` with async callback | `const ps = ["1", "2"].map(async id => getUser(id));` | `ps` is an ARRAY of two Promises; `ps[0].name` is `undefined` |
| 15 | async IIFE | `const p = (async () => { await save(); })();` | a Promise (dropped if the call is a bare statement) |

**Returns a value (not a ticket)**

| # | Form | Concrete example | What you hold |
| --- | --- | --- | --- |
| 16 | `JSON.parse` | `const o = JSON.parse('{"a":1}');` | the object now; `o.a` is 1 |
| 17 | array methods | `const b = [1, 2].map(x => x * 2);` | `[2, 4]` now. If the callback were async, `b` would hold Promises, but `map` itself is synchronous |
| 18 | string methods | `const u = "a".toUpperCase();` | `"A"` now |
| 19 | `Math.*`, `Date.now()` | `const m = Math.max(1, 2);` | 2 now |
| 20 | `readFileSync` | `const t = fs.readFileSync("a.txt", "utf8");` | the string now; blocks the process while reading |
| 21 | timers | `const id = setTimeout(fn, 10);` | a timer id (number in browsers, a `Timeout` object in Node), not a Promise |
| 22 | Express `res.*` | `res.status(404).json({ error: "x" });` | sends the response; each call returns `res`; none is a Promise; the function keeps running |
| 23 | misc sync | `localStorage.setItem("k", "v")` gives `undefined`; `console.log(1)` gives `undefined`; `crypto.randomUUID()` gives a string | values now |
| 24 | `new` of an ordinary class | `const m = new Map();` | the Map now |
| 25 | `forEach` with async callback | `const r = ids.forEach(async id => await save(id));` | `r` is `undefined`; the Promises were dropped |

**How the ticket is handled on this line**

| # | Form | Concrete example | Verdict |
| --- | --- | --- | --- |
| 26 | `await` into a label | `const v = await f();` with `f` resolving to 1 | `v` holds 1 (the value) |
| 27 | `return f()` inside async | `async function g() { try { return f(); } catch (e) { log(e) } }` | `f`'s Promise leaves `g`'s `try` pending; if `f` rejects, `log` never runs |
| 28 | `return await f()` inside async | `async function g() { try { return await f(); } catch (e) { log(e) } }` | if `f` rejects, the error is thrown inside the `try`; `log` runs |
| 29 | `.then` chain with handlers | `f().then(g).catch(h);` | handled by the chain; the chain's own result is still a Promise |
| 30 | `await Promise.all` | `const all = await Promise.all([f(), g()]);` | `all` is `[1, 2]`; parallel; rejects on the first failure |
| 31 | deferred `await` | `const p = f(); other(); const v = await p;` | `f` and `other` overlap in time; `v` is the value |
| 32 | bare async call | `f();` | dropped; if `f` rejects, unhandled rejection |
| 33 | ticket used as value | `const v = f(); v.name` | `undefined` (a Promise has no `name`) |
| 34 | `await` inside `forEach` | `ids.forEach(async id => { await save(id); }); log("done");` | `"done"` logs BEFORE any save finishes |
| 35 | `await` in a non-async function | `function g() { const v = await f(); }` | SyntaxError: `await` is only valid in an async function |

# Q5. Can it be nothing?

**Yes, it can be `undefined`**

| # | Source | Concrete example | Result |
| --- | --- | --- | --- |
| 1 | optional property | `const u: { email?: string } = {}; u.email` and `u.email.length` | `undefined`; then TypeError on `.length` |
| 2 | loose type | `const d = JSON.parse("{}"); d.user` and `d.user.name` | `undefined`; then TypeError |
| 3 | `find` miss | `[1, 2].find(x => x > 5)` and `[].findLast(x => x)` | `undefined`, `undefined` |
| 4 | index out of range | `[1, 2][2]` and `[1, 2].at(5)` | `undefined`, `undefined` |
| 5 | always-undefined index | `[1, 2][-1]` and `arr[arr.length]` | `undefined` even though the array is non-empty |
| 6 | `Map.get` miss | `new Map().get("a")` | `undefined` |
| 7 | `pop` / `shift` on empty | `[].pop()` and `[].shift()` | `undefined`, `undefined` |
| 8 | request fields | `GET /users` with no query: `req.query.page`; no header: `req.headers["x-key"]` | `undefined`, `undefined` |
| 9 | environment | `process.env.NOPE` | `undefined` |
| 10 | function falls off the end | `function f(x) { if (x) return 1; }` then `f(0)` | `undefined` |
| 11 | braces without `return` | `[1, 2].map(x => { x * 2 })` | `[undefined, undefined]` |
| 12 | declared, never assigned | `let x; x` | `undefined` |
| 13 | optional chain | `const o = null; o?.k` | `undefined` |
| 14 | destructuring a missing key | `const { a } = {};` | `a` holds `undefined` |
| 15 | default parameter | `function f(n = 5) { return n }`: `f()`, `f(undefined)`, `f(null)` | 5, 5, `null` (default fires only for `undefined`) |
| 16 | first of an empty list | `Object.values({})[0]` | `undefined` |
| 17 | missing regex group | `"ab".match(/(x)/)?.[1]` | `undefined` (match is `null`, `?.` stops) |
| 18 | never settles | `await Promise.race([])` | not `undefined`: the function hangs forever |

**Yes, it can be `null`**

| # | Source | Concrete example | Result |
| --- | --- | --- | --- |
| 19 | explicit `null` | `let x = null;` | `null` |
| 20 | database lookup | `await db.user.findOne({ id: "none" })` | `null` |
| 21 | `JSON.parse("null")` | `JSON.parse("null")` | `null` |
| 22 | `localStorage` miss | `localStorage.getItem("none")` | `null` |
| 23 | regex miss | `"abc".match(/x/)` and `/x/.exec("abc")` | `null`, `null` |
| 24 | DOM lookup | `document.querySelector("#none")` | `null` |
| 25 | declared `T \| null` | `function f(): string \| null { return Math.random() > 2 ? "a" : null }` | `null` (always, for this input) |
| 26 | `null` passed to a default | `function f(n = 5) { return n } f(null)` | `null`, NOT 5 |

**No, it cannot be nothing (unless a type lies)**

| # | Source | Concrete example | Result |
| --- | --- | --- | --- |
| 27 | a literal | `const a = 5; a` | 5 |
| 28 | lengths and sizes | `[].length` and `new Map().size` | 0, 0 (numbers, never `undefined`) |
| 29 | array-returning methods | `[].filter(x => x)`, `Object.keys({})`, `[1].map(x => x)` | `[]`, `[]`, `[1]` (empty, but an array) |
| 30 | `new` | `new Date()` | a Date object |
| 31 | `Number(x)` | `Number("abc")` | `NaN` (a number; nothing-like, but not `undefined`) |
| 32 | `String(x)` and templates | `String(undefined)` | `"undefined"` (a string) |
| 33 | predicates | `[1].includes(2)` | `false` |
| 34 | awaited, honestly typed | `const u = await getUser("1")` with `getUser(): Promise<User>` that never resolves empty | a `User` |

**How the next use handles nothing (test each with `x = undefined`, `x = null`, `x = 0`)**

| # | Form | `x = undefined` | `x = null` | `x = 0` | Verdict |
| --- | --- | --- | --- | --- | --- |
| 35 | `if (x) { ... }` | skipped | skipped | skipped | also skips `0`; wrong when 0 is valid |
| 36 | `if (!x) return;` | returns | returns | returns | same: also catches `0`, `""`, `false` |
| 37 | `if (x === undefined)` | true | false | false | precise for `undefined` only |
| 38 | `if (x == null)` | true | true | false | the idiomatic "nothing" check |
| 39 | `x ?? "d"` | `"d"` | `"d"` | 0 | falls back only for nothing |
| 40 | `x \|\| "d"` | `"d"` | `"d"` | `"d"` | falls back for 0 too: wrong for counts |
| 41 | `x?.k` | `undefined` | `undefined` | `undefined` (0 has no `k`) | safe access; result must be handled |
| 42 | `x!.k` | TypeError | TypeError | `undefined` | the `!` checks nothing |
| 43 | `x.k` | TypeError | TypeError | `undefined` | crashes on nothing |
| 44 | `typeof x === "string"` | false | false | false | no crash; says "not a string" |
| 45 | `Array.isArray(x)` | false | false | false | no crash |
| 46 | `x instanceof Date` | false | false | false | no crash |
| 47 | `"k" in x` | TypeError | TypeError | TypeError | `in` needs an object on the right |

# Q6. Who else points here?

**This line made a NEW address (own)**

| # | Form | Concrete example | Result |
| --- | --- | --- | --- |
| 1 | object literal | `const p = {}; const q = {};` | `p === q` is `false`: two objects |
| 2 | array literal | `const p = [1]; const q = [1];` | `p === q` is `false` |
| 3 | `{ ...o }` | `const o = { a: 1, i: { x: 1 } }; const c = { ...o };` | `c !== o`; but `c.i === o.i` (inner object shared) |
| 4 | `[...a]` | `const a = [{ n: 1 }]; const c = [...a];` | `c !== a`; but `c[0] === a[0]` |
| 5 | `slice` / `Array.from` / `concat` | `const a = [1, 2]; const c = a.slice();` | `c !== a`; `c.push(3)` leaves `a` as `[1, 2]` |
| 6 | `map` / `filter` | `const users2 = users.filter(u => u.active);` | `users2 !== users`; `users2[0] === users[i]` (same user objects) |
| 7 | `toSorted` / `toReversed` | `const a = [3, 1]; const s = a.toSorted();` | `s` is `[1, 3]`; `a` is still `[3, 1]` |
| 8 | `Object.assign({}, o)` and friends | `const c = Object.assign({}, { a: 1 });` and `Object.fromEntries([["a", 1]])` | new objects, shallow |
| 9 | `new Map(m)` / `new Set(s)` | `const m2 = new Map(m);` | `m2 !== m`; `m2.set("x", 1)` leaves `m` alone |
| 10 | `structuredClone` | `const o = { a: { b: 1 } }; const c = structuredClone(o); c.a.b = 9;` | `o.a.b` is still 1 (deep) |
| 11 | JSON round trip | `JSON.parse(JSON.stringify({ d: new Date(0) }))` | deep, but `d` becomes the string `"1970-01-01T00:00:00.000Z"`; `undefined` values and functions vanish |
| 12 | `new C()` | `const a = new User(); const b = new User();` | `a !== b` |
| 13 | function literal | `const f = () => {}; const g = () => {};` | `f !== g` |
| 14 | `split` / `groupBy` | `"a,b".split(",")` and `Object.groupBy(arr, f)` | new array / new object |
| 15 | function returning a literal | `function f() { return []; }` | `f() !== f()`: a new array per call |

**This line made an ALIAS (shared with something else)**

| # | Form | Concrete example | Result |
| --- | --- | --- | --- |
| 16 | `const b = a;` | `const a = [1]; const b = a; b.push(2);` | `a` is `[1, 2]` |
| 17 | function parameter | `function f(xs) { xs.push(1); } const a = []; f(a);` | `a` is `[1]`: the caller's array changed |
| 18 | `find` / `[i]` / `at` | `const u = users.find(p); ` and `users[0]` | `u === users[k]`: the same user object; `u.name = "x"` changes the one in `users` |
| 19 | `map.get(k)` | `const m = new Map([["k", { n: 1 }]]); const v = m.get("k"); v.n = 2;` | `m.get("k").n` is 2 |
| 20 | `o.k` where the value is an object | `const o = { inner: { x: 1 } }; const i = o.inner;` | `i === o.inner`; `i.x = 2` changes `o.inner.x` |
| 21 | `const { inner } = o` | same `o` | `inner === o.inner`; identical to row 20 |
| 22 | returning internal state | `class A { items = []; get() { return this.items; } }` then `a.get().push(1)` | `a.items` is `[1]`: the caller edited internal state |
| 23 | cache hands out the stored object | `cache.set(k, obj); return obj;` then the caller does `obj.n = 5` | the cache entry now has `n` = 5 for every later hit |
| 24 | closure captures an object | `const o = { n: 1 }; const f = () => o.n; o.n = 2; f()` | 2: the closure reads the live object |
| 25 | `sort` / `reverse` / `fill` return the same array | `const a = [3, 1]; const s = a.sort();` | `s === a` is `true`; both are `[1, 3]` |
| 26 | `Object.assign(target, src)` | `const t = {}; const r = Object.assign(t, { a: 1 });` | `r === t` is `true`; `t` is `{ a: 1 }` |
| 27 | elements of a `filter` / `map(x => x)` result | `const f = users.filter(p); f[0].name = "z";` | the matching user in `users` has name `"z"` |
| 28 | `forEach` callback parameter | `orders.forEach(o => { o.status = "paid"; });` | every order in `orders` is now paid |
| 29 | module-level state | `const state = {}; export function add(k) { state[k] = 1; }` | every importer and every request shares `state` |
| 30 | `this` in a method | `class A { n = 0; inc() { this.n++; } }` | `a.inc()` changes that instance for everyone holding `a` |

**Mutations that reach every alias**

| # | Form | Concrete example | Result |
| --- | --- | --- | --- |
| 31 | property or index set | `const a = [1]; const b = a; b[0] = 9;` | `a[0]` is 9 |
| 32 | `delete` | `const o = { k: 1 }; const p = o; delete o.k;` | `p.k` is `undefined` |
| 33 | push / pop / shift / unshift / splice | `const a = [1, 2, 3]; const b = a; a.splice(0, 1);` | `b` is `[2, 3]` |
| 34 | sort / reverse / fill / copyWithin | `const a = [3, 1]; const b = a; a.sort();` | `b` is `[1, 3]` |
| 35 | `length = n` | `const a = [1, 2]; const b = a; a.length = 0;` | `b` is `[]` |
| 36 | `Map` / `Set` mutators | `const m = new Map(); const n = m; m.set("a", 1);` | `n.get("a")` is 1 |
| 37 | `Date` setters | `const d = new Date(0); const e = d; d.setFullYear(2000);` | `e.getFullYear()` is 2000 |
| 38 | `Object.assign(o, src)` | `const o = { a: 1 }; const p = o; Object.assign(o, { a: 2 });` | `p.a` is 2 |
| 39 | `freeze` / `defineProperty` | `const o = { a: 1 }; Object.freeze(o); o.a = 2;` | `o.a` is still 1 (silently ignored, or TypeError in strict mode); freeze is shallow |
| 40 | nested set | `const o = { n: { k: 1 } }; const s = o.n; o.n.k = 2;` | `s.k` is 2 |
| 41 | mutate each element | `const a = [{ v: 1 }, { v: 2 }]; const b = a; a.forEach(x => { x.v = 0; });` | `b[1].v` is 0 |
| 42 | regex with `g` | `const re = /a/g; re.exec("aa"); re.lastIndex` | 1: calling `exec` advanced shared state; a module-level `/a/g` used in two places interferes with itself |

**Who the "else" usually is**

| # | Holder | Concrete example | How to spot it |
| --- | --- | --- | --- |
| 43 | the caller | `function f(opts) { opts.retries = 5; }` then `f(config)` | `config.retries` is now 5; the object came in as a parameter |
| 44 | the module (every request) | `const cache = new Map();` at the top of a file | declared outside any function |
| 45 | the class (every method) | `this.items.push(x)` in one method, read in another | `this.` on a field |
| 46 | the cache | `const v = cache.get(k); v.hits++;` | the object came from a get on a long-lived Map |
| 47 | the original array | `const first = users.find(p); first.active = false;` | the object was an element from `find`, `[i]`, or `filter` |
| 48 | a previous caller | `const DEFAULT = {}; function f() { return DEFAULT; }` | `f()` returns the SAME object every call |
| 49 | a listener or timer | `setInterval(() => use(big), 1000);` | the closure keeps `big` alive and shared |
| 50 | defaults / config | `const opts = defaults; opts.x = 1;` | missing `{ ...defaults }`; `defaults.x` is now 1 for everyone |

# Q7. Was the result kept?

**Kept (the value goes somewhere)**

| # | Form | Concrete example | Where it went |
| --- | --- | --- | --- |
| 1 | assigned | `const x = f(); o.k = f();` | into `x`; into `o.k` |
| 2 | returned | `return f();` | to the caller |
| 3 | awaited into a label | `const x = await f();` | the resolved value into `x` |
| 4 | passed as an argument | `g(f()); arr.push(f()); res.json(f());` | into `g`; onto the array; into the response |
| 5 | used in a condition | `if (f()) {}`; `while (f()) {}`; `f() ? a : b` | decided the branch |
| 6 | used in an expression | `a + f()`; `` `${f()}` `` | became part of a larger value |
| 7 | stored | `map.set(k, f()); arr[i] = f();` | into the Map; into the slot |
| 8 | spread | `[...f()]`; `({ ...f() })` | copied into a new container |
| 9 | destructured | `const { a } = f();` | `a` holds `f().a` |
| 10 | chained | `f().g()` | the next call consumed it |
| 11 | yielded | `yield f();` | handed to the generator's caller |
| 12 | thrown | `throw f();` | became the exception |

**Not kept, and that is fine (the effect was the point)**

| # | Form | Concrete example | What the effect was |
| --- | --- | --- | --- |
| 13 | mutating call | `arr.push(x);` with `arr = [1]`, `x = 2` | `arr` became `[1, 2]`; the returned length 2 is dropped |
| 14 | property set | `o.k = v;` | `o.k` now holds `v` |
| 15 | side-effect call | `console.log(x); res.json(d); emitter.emit("e"); clearTimeout(id);` | printed; sent; notified listeners; cancelled the timer |
| 16 | awaited, value dropped | `await save(x);` | waited until `save` finished |
| 17 | `void` | `void f();` | explicit "I am ignoring this" |
| 18 | sync call with documented effect | `logger.info("started");` | wrote a log line |

**Not kept, and that is the bug**

| # | Form | Concrete example | What went wrong |
| --- | --- | --- | --- |
| 19 | non-mutating array method | `[1, 2].map(x => x * 2);` (also `filter`, `slice`, `concat`, `flat`) | a new array `[2, 4]` built and dropped; dead line |
| 20 | non-mutating twins | `arr.toSorted();` and `arr.toReversed();` | new array dropped |
| 21 | string method | `let s = " a "; s.trim();` | `s` is still `" a "`; the `"a"` was dropped |
| 22 | copy dropped | `({ ...o });` and `[...a];` and `Object.assign({}, o);` | a copy built and dropped |
| 23 | clone / parse dropped | `structuredClone(o);` and `JSON.parse(s);` | result dropped (and `JSON.parse` may still throw) |
| 24 | lookup dropped | `arr.find(p);` and `arr.includes(x);` and `map.get(k);` | looked something up and ignored the answer |
| 25 | async call, no await | `save(x);` | Promise dropped; rejection unhandled; next line runs too early |
| 26 | `fetch` dropped | `fetch(url);` | request sent; response and errors ignored |
| 27 | async `map` dropped | `ids.map(async id => save(id));` | an array of Promises dropped; nothing waits |
| 28 | `.then` with no `.catch` | `p.then(g);` | a rejection of `p` or `g` is unhandled |
| 29 | pure expression | `x;` and `a + b;` and `o.k;` | evaluated and discarded |
| 30 | `new` dropped | `new Date();` and `new User();` | an object built and dropped |
| 31 | async IIFE, no catch | `(async () => { await save(x); })();` | Promise dropped; errors unhandled |
| 32 | kept, but misleading: `sort` | `const sorted = arr.sort();` | kept, but `sorted === arr`: both reordered; not a copy |
| 33 | kept, but not what you think: `push` | `const n = arr.push(x);` | `n` is the new LENGTH (a number), not the array |

# The note, with every field and an example of each

After Q7 write: **`label` holds: value · own or shared · can be nothing · ticket or value.**

| Field | Options | Example |
| --- | --- | --- |
| value | a concrete example | `6`, `"ABC"`, `{ id: "42", name: "Ann" }`, `[1, 10, 9]`, `Promise<User>`, `undefined` |
| own or shared | own (new address) / shared with the caller, `users[]`, the cache, module state, `defaults` | `user holds: an element of users[], shared` |
| can be nothing | yes (and why) / no | `yes: find miss` |
| ticket or value | value / ticket not awaited / ticket awaited on line N | `ticket, not awaited` |

Whole notes, written out: `user holds: a User object, shared with users[], can be undefined (find miss), value` and `p holds: Promise<User>, own, cannot be nothing, ticket not awaited (BUG)`.

The next line's Q4 reads "ticket or value", its Q5 reads "can be nothing", and its Q6 reads "own or shared". That is the entire hand-off.
