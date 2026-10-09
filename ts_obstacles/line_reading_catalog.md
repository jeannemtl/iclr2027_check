---
title: "Reading One Line: the Catalog"
subtitle: "Every option at every one of the seven questions, itemized, with the example form and what it means for the note"
date: "October 2026"
---

**How to use.** This is the lookup behind the seven-question method. At each question, find the row that matches the line in front of you; the last column tells you what to carry into the note or the next question. Rows are exhaustive for the code you will meet in a review; anything not listed is rare enough to look up.

# Q1. What kind of line is it?

**Declarations (a new label or type comes into existence)**

| # | Form | Example | Carry forward |
| --- | --- | --- | --- |
| 1 | `const` with value | `const a = 1;` | label fixed; go to Q2 on the right side |
| 2 | `let` with value | `let a = 1;` | label may be reassigned later |
| 3 | `let` without value | `let a;` / `let a: number;` | holds `undefined` until assigned |
| 4 | `var` | `var a = 1;` | function-scoped, hoisted; smell |
| 5 | destructuring object | `const { a, b } = o;` | two labels; each is a property read of `o` |
| 6 | destructuring with rename | `const { a: x } = o;` | label `x` holds `o.a` |
| 7 | destructuring with default | `const { a = 5 } = o;` | `a` is `o.a` unless `undefined`, then 5 |
| 8 | destructuring rest | `const { a, ...rest } = o;` | `rest` is a NEW shallow object of the other keys |
| 9 | destructuring array | `const [x, y] = arr;` | `x` is `arr[0]`, `y` is `arr[1]`, either may be `undefined` |
| 10 | destructuring array rest | `const [h, ...t] = arr;` | `t` is a NEW array |
| 11 | function declaration | `function f(x: number) {}` | hoisted; a function object |
| 12 | async function declaration | `async function f() {}` | returns a Promise, always |
| 13 | generator | `function* g() {}` | returns an iterator |
| 14 | class | `class A {}` | a constructor; `new A()` makes instances |
| 15 | class field | `count = 0;` inside a class | per-instance property |
| 16 | class method | `m() {}` inside a class | on the prototype; `this` is the instance when called as `a.m()` |
| 17 | getter / setter | `get x() {}` / `set x(v) {}` | read as `a.x`; no parentheses |
| 18 | static member | `static n = 0;` / `static f() {}` | on the class, not instances |
| 19 | `interface` | `interface U { id: number }` | type-only; runs nothing |
| 20 | `type` alias | `type Id = string \| number;` | type-only |
| 21 | `enum` | `enum C { A, B }` | a real object at runtime; numeric by default |
| 22 | `import` | `import { x } from "./m";` | a label bound to another module's export |
| 23 | `export` | `export const a = 1;` / `export default f` | same as the declaration, plus visibility |
| 24 | `declare` | `declare const g: string;` | type-only; exists elsewhere |

**Assignments (an existing label re-pointed, or an object mutated)**

| # | Form | Example | Carry forward |
| --- | --- | --- | --- |
| 25 | reassignment | `a = 2;` | label re-pointed; needs `let` |
| 26 | compound | `a += 1;`, `a -= 1;`, `a *= 2;`, `s += "x";` | reassignment with arithmetic or concat |
| 27 | increment | `i++;`, `++i;`, `i--;` | reassignment |
| 28 | logical assignment | `a \|\|= b;`, `a &&= b;`, `a ??= b;` | reassign only if falsy / truthy / nullish |
| 29 | property set | `o.k = v;` | MUTATES `o`; every alias sees it |
| 30 | bracket set | `o["k"] = v;`, `arr[i] = v;` | mutates |
| 31 | nested set | `o.a.b = v;` | mutates `o.a`, which may be shared with something else |
| 32 | delete | `delete o.k;` | mutates |
| 33 | length set | `arr.length = 0;` | mutates; empties every alias |
| 34 | destructuring assignment | `({ a } = o);`, `[x, y] = [y, x];` | reassigns existing labels |
| 35 | chained assignment | `a = b = 0;` | both labels point at 0 |

**Expression statements (a bare expression; something runs, result dropped unless it mutates)**

| # | Form | Example | Carry forward |
| --- | --- | --- | --- |
| 36 | mutating method call | `arr.push(1);`, `arr.sort();`, `map.set(k, v);` | the mutation is the effect; fine |
| 37 | non-mutating method call | `arr.map(f);`, `s.trim();`, `arr.filter(p);` | result dropped; dead line |
| 38 | sync side-effect call | `console.log(x);`, `res.json(d);`, `emitter.emit(e);` | the side effect is the effect |
| 39 | async call, no await | `save(x);`, `fetch(url);` | fire-and-forget; rejection unhandled |
| 40 | `await` alone | `await save(x);` | waits; value dropped on purpose |
| 41 | `new` alone | `new Worker(...);` | side effect of construction; object dropped |
| 42 | bare value | `x;`, `a + b;`, `o.k;` | does nothing |
| 43 | `void` expression | `void f();` | runs `f`, discards result; explicit fire-and-forget |
| 44 | IIFE | `(async () => { ... })();` | runs immediately; a Promise is dropped unless caught |

**Control (changes which line runs next)**

| # | Form | Example | Carry forward |
| --- | --- | --- | --- |
| 45 | `if` / `else if` / `else` | `if (x) {} else {}` | condition is coerced to boolean; check `=` vs `===` |
| 46 | ternary | `c ? a : b` | an expression, not a statement; has a value |
| 47 | `switch` | `switch (x) { case 1: ... }` | uses `===`; missing `break` falls through; missing `default` returns `undefined` |
| 48 | `for` | `for (let i = 0; i < n; i++)` | check the bound; `let` per iteration |
| 49 | `for...of` | `for (const x of arr)` | values; supports `break`, `await` |
| 50 | `for...in` | `for (const k in obj)` | keys as strings; on arrays, indices as strings |
| 51 | `while` / `do...while` | `while (cond) {}` | check termination |
| 52 | `break` / `continue` | | only in loops / `switch`; not in `forEach` |
| 53 | `return` | `return x;` / `return;` | ends the function; `return;` is `undefined` |
| 54 | `throw` | `throw new Error("m");` | unwinds to the nearest `try` on the same stack |
| 55 | `try` / `catch` / `finally` | `try {} catch (e) {} finally {}` | catches only what is thrown or awaited inside |
| 56 | labeled statement | `outer: for (...)` | rare; `break outer` |
| 57 | `yield` | `yield x;` | inside a generator |

**Type-only (runs nothing; note what the author claims)**

| # | Form | Example | Claim |
| --- | --- | --- | --- |
| 58 | annotation | `x: number` | `x` is a number here |
| 59 | return type | `): Promise<User>` | every path returns that |
| 60 | cast | `x as User` | trust me; no check |
| 61 | non-null | `x!` | not null; no check |
| 62 | `satisfies` | `o satisfies Config` | shape check without widening |
| 63 | generic parameter | `<T>` | placeholder |
| 64 | `as const` | `[...] as const` | literal types |
| 65 | `typeof x` in a type | `let y: typeof x` | same type as `x` |
| 66 | `keyof T` | | union of key names |
| 67 | `@ts-ignore` / `@ts-expect-error` | comment | checking off for the next line; a finding |

# Q2. Where does the value come from?

**Literals**

| # | Form | Example | Q3 answer |
| --- | --- | --- | --- |
| 1 | string | `"a"`, `'a'`, `` `a ${x}` `` | primitive |
| 2 | number | `42`, `3.5`, `-0`, `1e9`, `0x1f`, `NaN`, `Infinity` | primitive |
| 3 | boolean | `true`, `false` | primitive |
| 4 | nullish | `null`, `undefined` | primitive |
| 5 | bigint | `10n` | primitive |
| 6 | object literal | `{}`, `{ a: 1 }`, `{ a }`, `{ [k]: v }`, `{ ...o }` | object, NEW |
| 7 | array literal | `[]`, `[1, 2]`, `[...a, ...b]` | object, NEW |
| 8 | function literal | `() => {}`, `function () {}`, `async () => {}` | object (function), NEW |
| 9 | regex literal | `/ab+/g` | object, NEW |
| 10 | template literal | `` `Hello ${name}` `` | primitive string |
| 11 | `new` expression | `new Map()`, `new Set()`, `new Date()`, `new Error()`, `new C()` | object, NEW |

**Calls**

| # | Form | Example | Q4 applies? |
| --- | --- | --- | --- |
| 12 | plain function call | `f(x)` | yes: is `f` async? |
| 13 | method call | `obj.m(x)`, `arr.map(f)`, `s.trim()` | yes if the method is async; also note mutate vs new |
| 14 | optional call | `cb?.(x)` | may not run at all |
| 15 | constructor | `new C(x)` | not a Promise (unless `C` is `Promise`) |
| 16 | chained calls | `a.b().c().d()` | each `.` on the previous result; the last one's return is the value |
| 17 | IIFE | `(() => 5)()` | the arrow's return |
| 18 | tagged template | `` sql`...` `` | a function call |
| 19 | `await` of a call | `await f(x)` | Q4 answered: unwrapped |
| 20 | `.then` chain | `f().then(g)` | a Promise of `g`'s result |
| 21 | `Promise.all([...])` | | a Promise of an array |
| 22 | `JSON.parse(s)` | | sync; `any`; throws on bad input |
| 23 | `Number(x)`, `String(x)`, `Boolean(x)` | | conversion; `Number` may give `NaN` |
| 24 | `parseInt(s, 10)`, `parseFloat(s)` | | partial parse; `NaN` on failure |
| 25 | `Object.keys/values/entries(o)` | | new arrays |
| 26 | `Array.from(x)`, `Array.isArray(x)` | | new array / boolean |
| 27 | `structuredClone(o)` | | deep copy, new |
| 28 | `Date.now()` | | primitive number |
| 29 | `Math.*` | `Math.max(...arr)` | number; `-Infinity` on empty spread |

**Property and element reads**

| # | Form | Example | Can be nothing? |
| --- | --- | --- | --- |
| 30 | dot | `o.k` | yes if `k` is optional or absent |
| 31 | bracket, string key | `o["k"]`, `o[name]` | yes; also prototype keys on plain objects |
| 32 | index | `arr[i]`, `arr[0]`, `arr[arr.length - 1]` | yes past the end; `arr[-1]` is always `undefined` |
| 33 | `arr.at(i)` | | yes; `-1` works |
| 34 | `arr.length`, `s.length` | | number, never `undefined` |
| 35 | `map.size`, `set.size` | | number |
| 36 | `map.get(k)` | | yes when absent |
| 37 | optional chain | `o?.k`, `o?.[i]`, `o?.k?.j` | yes; by design |
| 38 | nested | `o.a.b.c` | crashes if any link is nothing |
| 39 | request fields | `req.params.id`, `req.query.x`, `req.body.x`, `req.headers["x"]` | yes; and the type is string / string[] / any |
| 40 | `this.field` | | depends on how the method was called |
| 41 | `process.env.X` | | `string \| undefined` |
| 42 | `localStorage.getItem(k)` | | `string \| null` |

**Operators**

| # | Form | Example | Result |
| --- | --- | --- | --- |
| 43 | arithmetic | `a + b`, `a - b`, `a * b`, `a / b`, `a % b`, `a ** b` | number; `+` concatenates if either side is a string; `/ 0` is `Infinity`; bad input is `NaN` |
| 44 | string concat | `"a" + x` | string; `x` coerced |
| 45 | comparison | `<`, `<=`, `>`, `>=` | boolean; `NaN` makes all `false`; check the boundary |
| 46 | equality | `===`, `!==` | boolean, strict |
| 47 | loose equality | `==`, `!=` | boolean, coerced; flag |
| 48 | logical AND | `a && b` | `a` if falsy, else `b` |
| 49 | logical OR | `a \|\| b` | `a` if truthy, else `b`; replaces `0`, `""`, `false` |
| 50 | nullish | `a ?? b` | `a` unless `null`/`undefined` |
| 51 | NOT | `!x`, `!!x` | boolean; `!x` is true for `0`, `""`, `[]` is NOT falsy |
| 52 | ternary | `c ? a : b` | `a` or `b` |
| 53 | spread in literal | `[...a]`, `{ ...o }` | new container, shallow |
| 54 | `typeof x` | | a string naming the type |
| 55 | `x instanceof C` | | boolean |
| 56 | `k in o` | | boolean; includes prototype keys |
| 57 | `delete o.k` | | boolean; mutates |
| 58 | `void x` | | `undefined` |
| 59 | comma | `(a, b)` | `b`; rare |
| 60 | assignment as expression | `if (x = 5)` | the assigned value; always a bug in a condition |
| 61 | bitwise | `a & b`, `a \| b`, `a ^ b`, `~a`, `a << 1` | integer math; rare; `\|` in a value position is bitwise, in a type position is union |

**`await` and destructuring**

| # | Form | Example | Result |
| --- | --- | --- | --- |
| 62 | `await p` | | the resolved value; throws on rejection |
| 63 | `await nonPromise` | `await 5` | `5`; harmless; still yields |
| 64 | `const { a } = o` | | `o.a`; may be `undefined` |
| 65 | `const [x] = arr` | | `arr[0]` |
| 66 | `const { a: { b } } = o` | | `o.a.b`; crashes if `o.a` is nothing |
| 67 | `for (const [k, v] of map)` | | each entry |
| 68 | `for (const [k, v] of Object.entries(o))` | | each key-value pair |

# Q3. Primitive or object?

**Primitives (immutable, by value, copied, no keys)**

| # | Type | Produced by |
| --- | --- | --- |
| 1 | `string` | string literal, template, every string method, `String(x)`, `JSON.stringify`, `s.join`, `typeof` |
| 2 | `number` | numeric literal, arithmetic, `Number(x)`, `parseInt`, `arr.length`, `map.size`, `Date.now()`, `arr.indexOf`, `arr.push` (returns length), `Math.*` |
| 3 | `boolean` | `true`/`false`, comparisons, `===`, `!x`, `arr.includes`, `arr.some/every`, `map.has`, `Array.isArray`, `instanceof`, `in`, `delete`, `set.delete` |
| 4 | `undefined` | `let x;`, missing key, `arr[i]` past end, `map.get` miss, `find` miss, no `return`, `void`, `o?.k` short-circuit |
| 5 | `null` | `null` literal, DB not-found, `JSON.parse("null")`, `localStorage.getItem` miss, `regex.exec` miss |
| 6 | `bigint` | `10n`, `BigInt(x)` |
| 7 | `symbol` | `Symbol()`, `Symbol.iterator` |

**Objects (mutable, by identity, aliased, have keys)**

| # | Kind | Produced by |
| --- | --- | --- |
| 8 | plain object | `{}` literal, `{ ...o }`, `Object.assign`, `JSON.parse`, `Object.fromEntries`, `req.body`, `req.query` |
| 9 | array | `[]` literal, `[...a]`, `map`, `filter`, `slice`, `concat`, `flat`, `split`, `Object.keys/values/entries`, `Array.from`, `toSorted` |
| 10 | `Map` / `Set` | `new Map()`, `new Set()`, `new Map(m)`, `Map.groupBy` |
| 11 | function | function literal, arrow, method reference `obj.m`, `fn.bind(x)` |
| 12 | Promise | any `async` call, `fetch`, `res.json`, `new Promise`, `.then`, `Promise.all` |
| 13 | `Date` | `new Date()` |
| 14 | `Error` | `new Error()`, `catch (e)` (as `unknown`) |
| 15 | `RegExp` | `/x/`, `new RegExp` |
| 16 | class instance | `new C()` |
| 17 | iterator | `arr.entries()`, `map.keys()`, generator call |
| 18 | `Response` / `Request` / `Headers` / `URL` | `fetch`, `new URL(s)` |
| 19 | Buffer / typed array | `Buffer.from`, `new Uint8Array` |
| 20 | `req` / `res` / client / emitter | framework-provided |

# Q4. Ticket or value?

**Returns a Promise (a ticket)**

| # | Form | Note |
| --- | --- | --- |
| 1 | any function declared `async` | guaranteed |
| 2 | any function annotated `: Promise<...>` | guaranteed |
| 3 | `fetch(url)` | resolves on any HTTP status |
| 4 | `res.json()`, `res.text()`, `res.blob()`, `res.arrayBuffer()` | |
| 5 | `new Promise(...)`, `Promise.resolve`, `Promise.reject` | |
| 6 | `Promise.all`, `allSettled`, `race`, `any` | |
| 7 | `p.then(f)`, `p.catch(f)`, `p.finally(f)` | chaining always yields a Promise |
| 8 | `import("./m")` | dynamic import |
| 9 | `fs/promises` anything, `timers/promises`, `stream/promises` | |
| 10 | `util.promisify(fn)(...)` | |
| 11 | `db.query`, `pool.query`, `prisma.*`, `Model.find`, `collection.insertOne`, `redis.get`, `knex(...)` awaited | every DB client |
| 12 | `axios.get`, `got`, `ky`, `client.send(cmd)` | every HTTP client / SDK |
| 13 | a plain function whose body `return`s any of the above | pass-through |
| 14 | `arr.map(async x => ...)` | an ARRAY of Promises; needs `Promise.all` |
| 15 | an `async` IIFE | |

**Returns a value (not a ticket)**

| # | Form | Note |
| --- | --- | --- |
| 16 | `JSON.parse`, `JSON.stringify` | sync |
| 17 | all array methods (`map`, `filter`, `find`, `sort`, `push`...) | sync; the callbacks may be async but the method is not |
| 18 | all string methods | sync |
| 19 | `Object.*`, `Math.*`, `Number(...)`, `Date.now()` | sync |
| 20 | `fs.readFileSync` and every `*Sync` | sync, blocking |
| 21 | `setTimeout`, `setInterval` | return an id, not a Promise |
| 22 | `res.json(d)`, `res.send`, `res.status` (Express) | sync; chainable; do not end the function |
| 23 | `localStorage.*`, `console.*`, `crypto.randomUUID` | sync |
| 24 | `new C()` for any ordinary class | sync |
| 25 | `arr.forEach(async ...)` | returns `undefined`; the Promises are dropped |

**How the ticket is handled on this line**

| # | Form | Verdict |
| --- | --- | --- |
| 26 | `const v = await f()` | unwrapped; `v` is the value |
| 27 | `return f()` inside async | handed to the caller; not caught by this `try` |
| 28 | `return await f()` | unwrapped then returned; caught by this `try` |
| 29 | `f().then(g).catch(h)` | handled via chain; the chain's result still needs catching |
| 30 | `await Promise.all(arr)` | all unwrapped into an array |
| 31 | `const p = f()` then `await p` later | deferred; fine if the `await` comes before the value is used and inside the right `try` |
| 32 | `f();` | dropped; fire-and-forget |
| 33 | `const v = f()` then `v.x` | ticket used as value; `undefined` |
| 34 | `await` inside `forEach` callback | not waited for by anyone |
| 35 | `await` inside a non-async function | syntax error |

# Q5. Can it be nothing?

**Yes, it can be `undefined`**

| # | Source | Example |
| --- | --- | --- |
| 1 | optional property | `o.a` where `a?: T` |
| 2 | absent property on a loose type | `(o as any).x`, `JSON.parse(s).x` |
| 3 | `arr.find`, `findLast` | no match |
| 4 | `arr[i]`, `arr.at(i)` | out of range |
| 5 | `arr[arr.length]`, `arr[-1]` | always |
| 6 | `map.get(k)`, `weakMap.get(k)` | absent key |
| 7 | `arr.pop()`, `arr.shift()` | empty array |
| 8 | `req.headers[k]`, `req.query.k`, `req.params.k`, `req.body.k` | not sent |
| 9 | `process.env.X` | not set |
| 10 | a function with a fall-off path | no `return` on that path |
| 11 | `=> { ... }` with no `return` | always |
| 12 | `let x;` before assignment | |
| 13 | any `o?.k` | short-circuit |
| 14 | destructuring a missing key | `const { a } = {}` |
| 15 | default param when caller passes `undefined` explicitly | default applies, so NOT nothing; but passes `null` → `null` |
| 16 | `Object.values(o)[0]` | empty object |
| 17 | `str.match(re)?.[1]` | no match / no group |
| 18 | `Promise.race([])` | never settles; rare |

**Yes, it can be `null`**

| # | Source | Example |
| --- | --- | --- |
| 19 | explicit `null` | `let x = null` |
| 20 | DB row lookup | `findOne` → `null` |
| 21 | `JSON.parse("null")` | |
| 22 | `localStorage.getItem(k)` | miss |
| 23 | `regex.exec(s)`, `s.match(re)` | no match |
| 24 | `document.querySelector` | browser; not found |
| 25 | a `T \| null` return type | by declaration |
| 26 | a default param when the caller passes `null` | default does not apply |

**No, it cannot be nothing (unless the type lies)**

| # | Source |
| --- | --- |
| 27 | a literal |
| 28 | `arr.length`, `s.length`, `map.size` (a number) |
| 29 | `map`, `filter`, `slice`, `Object.keys` (an array, possibly empty) |
| 30 | `new C()` |
| 31 | `Number(x)` (a number, possibly `NaN`, never `undefined`) |
| 32 | `String(x)`, template literals |
| 33 | `arr.includes`, `map.has`, comparisons (a boolean) |
| 34 | `await f()` where `f` is declared `Promise<T>` with `T` non-nullable, and the declaration is honest |

**How the next use handles nothing**

| # | Form | Handles `undefined`? | Handles `null`? | Also catches `0`/`""`/`false`? |
| --- | --- | --- | --- | --- |
| 35 | `if (x)` / `x && x.k` | yes | yes | YES (wrong for counts, flags) |
| 36 | `if (!x) return` | yes | yes | YES |
| 37 | `if (x === undefined)` | yes | no | no |
| 38 | `if (x == null)` | yes | yes | no (the one idiomatic `==`) |
| 39 | `x ?? d` | yes | yes | no |
| 40 | `x \|\| d` | yes | yes | YES |
| 41 | `x?.k` | yes | yes | no |
| 42 | `x!.k` | claims no; checks nothing | | |
| 43 | `x.k` | not handled; crashes | | |
| 44 | `typeof x === "string"` | yes (it is not a string) | yes | no |
| 45 | `Array.isArray(x)` | yes | yes | no |
| 46 | `x instanceof C` | yes | yes | no |
| 47 | `"k" in x` | crashes on `undefined`/`null` | | |

# Q6. Who else points here?

**This line made a NEW address (own)**

| # | Form |
| --- | --- |
| 1 | object literal `{}`, `{ a: 1 }` |
| 2 | array literal `[]`, `[1, 2]` |
| 3 | `{ ...o }`, `{ ...a, ...b }` (new outer; inner objects shared) |
| 4 | `[...a]`, `[...a, ...b]` (new outer; elements shared) |
| 5 | `a.slice()`, `a.slice(i, j)`, `Array.from(a)`, `a.concat(b)` |
| 6 | `a.map(f)`, `a.filter(p)`, `a.flat()`, `a.flatMap(f)` (elements shared) |
| 7 | `a.toSorted()`, `a.toReversed()`, `a.toSpliced()`, `a.with(i, v)` |
| 8 | `Object.assign({}, o)`, `Object.fromEntries(...)`, `Object.keys/values/entries(o)` |
| 9 | `new Map(m)`, `new Set(s)`, `new Map()`, `new Set()` |
| 10 | `structuredClone(o)` (deep) |
| 11 | `JSON.parse(JSON.stringify(o))` (deep-ish) |
| 12 | `new C(...)`, `new Date()`, `new Error()` |
| 13 | a function literal |
| 14 | `s.split(...)`, `Object.groupBy(...)`, `Map.groupBy(...)` |
| 15 | the return of any function that builds and returns a literal |

**This line made an ALIAS (shared with something else)**

| # | Form | Shared with |
| --- | --- | --- |
| 16 | `const b = a;` | `a` |
| 17 | a function parameter | the caller's argument |
| 18 | `arr.find(p)`, `arr[i]`, `arr.at(i)`, `arr[0]` | the element inside `arr` |
| 19 | `map.get(k)` | the value inside the map |
| 20 | `o.k`, `o.a.b` where the value is an object | the nested object inside `o` |
| 21 | `const { inner } = o` | `o.inner` |
| 22 | `return this.items` / `return cache.get(k)` | internal state, now held by the caller |
| 23 | `cache.set(k, obj)` then handing `obj` out | the cache and every recipient |
| 24 | a closure referencing an outer object | the outer scope |
| 25 | `a.sort()`, `a.reverse()`, `a.fill()` (return the same array) | `a` |
| 26 | `Object.assign(target, src)` returns `target` | `target` |
| 27 | elements of `a.filter(p)`, `a.map(x => x)` | the original elements |
| 28 | `arr.forEach((o) => ...)` callback parameter | the element |
| 29 | a module-level `const state = {}` referenced in a function | every caller of that module |
| 30 | `this` inside a method | the instance |

**Mutations that reach every alias**

| # | Form |
| --- | --- |
| 31 | `o.k = v`, `o[k] = v`, `arr[i] = v` |
| 32 | `delete o.k` |
| 33 | `arr.push`, `pop`, `shift`, `unshift`, `splice` |
| 34 | `arr.sort`, `reverse`, `fill`, `copyWithin` |
| 35 | `arr.length = n` |
| 36 | `map.set`, `map.delete`, `map.clear`; `set.add`, `set.delete`, `set.clear` |
| 37 | `date.setFullYear/Month/Date/Hours/Time` |
| 38 | `Object.assign(o, src)` (first argument) |
| 39 | `Object.freeze(o)`, `Object.defineProperty(o, ...)` |
| 40 | `o.nested.k = v` (mutates the nested object; reaches everyone sharing `o.nested`) |
| 41 | `arr.forEach((o) => o.k = v)` (mutates each element) |
| 42 | `regex.exec(s)` with the `g` flag (advances `lastIndex`) |

**Who the "else" usually is**

| # | Holder | How to spot |
| --- | --- | --- |
| 43 | the caller | the object came in as a parameter |
| 44 | the module / every request | a `const x = new Map()` or `{}` at module scope |
| 45 | the class / every method | `this.items` |
| 46 | the cache | `cache.get(k)` returned it |
| 47 | the original array | the object was an element from `find` / `[i]` / `filter` |
| 48 | a previous caller | the function returned the same object before |
| 49 | a listener or timer | a closure captured it |
| 50 | `defaults` / config | `const opts = defaults` instead of `{ ...defaults }` |

# Q7. Was the result kept?

**Kept (the value goes somewhere)**

| # | Form |
| --- | --- |
| 1 | assigned: `const x = ...`, `x = ...`, `o.k = ...` |
| 2 | returned: `return ...` |
| 3 | awaited into a label: `const x = await ...` |
| 4 | passed as an argument: `f(...)`, `arr.push(...)`, `res.json(...)` |
| 5 | used in a condition: `if (...)`, `while (...)`, `c ? ... : ...` |
| 6 | used in an expression: `a + f()`, `` `${f()}` `` |
| 7 | stored: `map.set(k, ...)`, `arr[i] = ...` |
| 8 | spread into a literal: `[...f()]`, `{ ...f() }` |
| 9 | destructured: `const { a } = f()` |
| 10 | chained: `f().g()` (the next call consumes it) |
| 11 | yielded: `yield ...` |
| 12 | thrown: `throw ...` |

**Not kept, and that is fine (the effect was the point)**

| # | Form |
| --- | --- |
| 13 | mutating call: `arr.push(x);`, `arr.sort();`, `map.set(k, v);`, `set.add(x);`, `arr.splice(i, 1);` |
| 14 | property set: `o.k = v;` |
| 15 | side-effect call: `console.log(x);`, `res.json(d);`, `emitter.emit(e);`, `logger.info(...)`, `clearTimeout(id);` |
| 16 | `await save(x);` (waited; result intentionally dropped) |
| 17 | `void f();` (explicit discard) |
| 18 | `f(x);` where `f` is sync and documented to have side effects |

**Not kept, and that is the bug**

| # | Form | Why |
| --- | --- | --- |
| 19 | `arr.map(f);`, `arr.filter(p);`, `arr.slice();`, `arr.concat(b);`, `arr.flat();` | new array dropped; dead line |
| 20 | `arr.toSorted();`, `arr.toReversed();` | new array dropped |
| 21 | `s.trim();`, `s.toUpperCase();`, `s.replace(...);`, `s.slice(...);` | new string dropped |
| 22 | `Object.assign({}, o);`, `{ ...o };`, `[...a];` | copy dropped |
| 23 | `structuredClone(o);`, `JSON.parse(s);` | result dropped |
| 24 | `arr.find(p);`, `arr.includes(x);`, `map.get(k);`, `map.has(k);` | lookup dropped |
| 25 | `f();` where `f` is async | Promise dropped; rejection unhandled |
| 26 | `fetch(url);` | same |
| 27 | `arr.map(async x => ...);` | array of Promises dropped |
| 28 | `p.then(g);` with no `.catch` and not awaited | chain dropped |
| 29 | `x;`, `a + b;`, `o.k;`, `arr[0];` | pure expression; nothing happens |
| 30 | `new Date();`, `new User();` | object dropped |
| 31 | `(async () => { ... })();` with no `.catch` | Promise dropped |
| 32 | `const sorted = arr.sort();` | kept, but NOT a copy: `sorted === arr`; the keeping misleads |
| 33 | `const n = arr.push(x);` | kept the length, not the array |

# The note, with every field

After Q7, write: **`label` holds: <value> · <own \| shared with X> · <can be nothing: yes/no> · <ticket \| value>**.

| Field | Options |
| --- | --- |
| value | a concrete example: `6`, `"ABC"`, `{ id: "42", name: "Ann" }`, `[1, 10, 9]`, `Promise<User>`, `undefined` |
| own / shared | own (new address); shared with: the caller / `users[]` / the cache / module state / `defaults` |
| can be nothing | yes (why: find miss, optional key, header absent) / no |
| ticket / value | value / ticket, not awaited / ticket, awaited on line N |

The next line's Q5 reads "can be nothing"; Q6 reads "own / shared"; Q4 reads "ticket / value". That is the entire hand-off.
