---
title: "Reading One Line"
subtitle: "The seven questions to ask of any TypeScript line, in order, with worked examples and the note you write before moving on"
date: "October 2026"
---

**The method.** For every line, ask the same seven questions in the same order, then write one note saying what the label on the left now holds, as a concrete value. The next line's questions read that note. Under a minute per line once it is a habit; the whole review is this pass, line by line, feeding the sixteen review questions.

# The seven questions

**Q1. What kind of line is it?** Exactly one of:

| Kind | Looks like | What to expect |
| --- | --- | --- |
| declaration | `const` / `let` / `function` / `class` / `interface` / `type` | a new label (or type) comes into existence |
| assignment | `x = ...`, `x += ...`, `o.k = ...`, `arr[i] = ...` | an existing label is re-pointed, or an object is mutated |
| expression statement | a bare call: `arr.push(1);`, `save();`, `name.trim();` | something runs; the result goes nowhere unless the call mutates |
| control | `if` / `for` / `while` / `return` / `throw` / `try` / `await` alone | changes which line runs next, or ends the function |
| type-only | after `:`, inside `interface` / `type`, `as T`, `x!` | runs nothing; skip Q3–Q7; note only what the author is claiming |

**Q2. Where does the value come from?** Find the right-hand side (after `=`, or the whole expression if there is no `=`). Name its producer:

| Producer | Examples |
| --- | --- |
| literal | `{}`, `[]`, `{ a: 1 }`, `"a"`, `5`, `true`, `null` |
| call | `f(x)`, `obj.method()`, `new C()`, `fetch(url)` |
| property read | `o.k`, `o["k"]`, `arr[i]`, `arr.length`, `map.get(k)` |
| operator | `a + b`, `a ?? b`, `a \|\| b`, `c ? a : b`, `!x`, `...a` |
| `await` | `await p`: the producer is whatever `p` resolves to |
| destructuring | `const { a } = o`: the producer is `o.a` |

**Q3. Primitive or object?** The value from Q2 is one of the seven primitives (`string`, `number`, `boolean`, `undefined`, `null`, `bigint`, `symbol`) or an object (array, plain object, `Map`, `Set`, `Date`, `Promise`, function, class instance). Primitive: immutable, compared by value, copied; Q6 does not apply. Object: mutable, compared by identity, aliased; Q6 applies.

**Q4. Ticket or value?** Only if Q2 was a call.

1. Does the call return a Promise? Yes if the function is declared `async`, annotated `: Promise<...>`, is `fetch` / `res.json` / `db.query` / `new Promise` / `.then` / anything from `fs/promises` or a client SDK, or its body `return`s one of those.
2. If yes: is there an `await` on this line, or is the result `return`ed, `.then`'d, or passed to `Promise.all`?
3. If no to step 2: the label holds the ticket, not the value. The next `.property` on it is `undefined`. Q7 answer is "not kept"; this is the missing-await finding.

**Q5. Can it be nothing?** Can the value from Q2 be `undefined` or `null`?

| Source of nothing | Why |
| --- | --- |
| a property marked `?` | may be absent |
| `arr.find(...)`, `arr.findLast(...)` | no match |
| `map.get(k)` | key absent |
| `arr[i]` | past the end, or a hole |
| `req.headers[...]`, `req.query.x`, `req.params.x`, `req.body.x` | not sent |
| a function with a path that falls off the end | no `return` on that path |
| `?.` anywhere in the expression | short-circuits to `undefined` |
| a database row lookup | not found, often `null` |
| `JSON.parse` of external data | any shape at all |
| a default parameter when the caller passed `null` | default applies only to `undefined` |

If yes: does the next use of this label check (`if (x)`, `x == null`, `x ?? d`, `x?.k`) or walk straight into `.something`? Also note whether the check uses `!x`, which wrongly treats `0`, `""` and `false` as nothing.

**Q6. Who else points here?** Only if Q3 was an object.

1. Did this line make a **new address**, or an **alias** to an existing one?

| New address | Alias |
| --- | --- |
| a literal `{}`, `[]`, `new Map()` | `= a` (another label) |
| `[...a]`, `{ ...o }`, `a.slice()`, `Array.from(a)` | a parameter (points at the caller's object) |
| `a.map(f)`, `a.filter(p)`, `a.concat(b)`, `toSorted`, `toReversed` | `find`, `arr[i]`, `map.get(k)` (the actual element, not a copy) |
| `structuredClone(o)` | `return this.items` (internal state handed out) |
| `JSON.parse(JSON.stringify(o))` | a cache hit |
| | a closure capturing an outer object |

2. If alias: does this line, or any later line, **mutate** it? (`push`, `pop`, `shift`, `unshift`, `splice`, `sort`, `reverse`, `fill`, `o.k = v`, `delete o.k`, `arr.length = 0`, `map.set`, `set.add`, `date.setX`.)
3. If alias and mutated: who else holds that address, and do they expect it unchanged? That is the finding.
4. Copies are shallow unless `structuredClone`: `{ ...o }` shares `o.inner`; `filter` shares the elements.

**Q7. Was the result kept?** Does the line's value go somewhere: assigned to a label, `return`ed, `await`ed, passed as an argument, used in a condition, or stored into an object or collection?

| Bare expression statement | Kept? | Verdict |
| --- | --- | --- |
| `arr.push(x);`, `arr.sort();`, `o.k = v;`, `map.set(k, v);` | the mutation IS the effect | fine |
| `arr.map(f);`, `arr.filter(p);`, `arr.slice();` | new array dropped | dead line |
| `s.trim();`, `s.toUpperCase();`, `s.replace(...)` | new string dropped | dead line |
| `fetch(url);`, `save(x);` (async, no `await`) | Promise dropped | fire-and-forget; rejection unhandled |
| `arr.map(async ...)` with no `Promise.all` | array of Promises dropped | same |
| `f(x);` where `f` is sync and has side effects | the side effect IS the effect | fine |
| `x;`, `a + b;`, `o.k;` | nothing | dead line |

# The note

After Q7, write one line: **`label` holds: <concrete value>, <shared or own>, <can be nothing or not>, <ticket or value>.** Examples:

- `user holds: a User object shared with users[], or undefined`
- `ids holds: a new number[] sorted as strings`
- `p holds: Promise<User>, a ticket, not awaited`
- `size holds: a number, possibly NaN, possibly 0`
- `opts holds: a new object; opts.inner is shared with defaults.inner`

The next line's Q5 and Q6 are answered by reading this note, not by re-deriving.

# Worked lines

**Line A**

```ts
const user = users.find((u) => u.id === req.params.id);
```

| Q | Answer |
| --- | --- |
| 1 | declaration with assignment |
| 2 | a call: `users.find(...)` with an arrow condition |
| 3 | object (a `User`) or `undefined` |
| 4 | `find` is synchronous; not a ticket |
| 5 | yes: `find` returns `undefined` when nothing matches; and `req.params.id` is a string, so if `u.id` is a number, `===` never matches and this is always `undefined` |
| 6 | alias: `find` returns the actual element; mutating `user.x` later mutates the element inside `users` |
| 7 | kept in `user` |
| note | `user` holds: a User object shared with `users[]`, or `undefined` |

Next line `res.json({ name: user.name })`: Q5 from the note says `user` can be `undefined`; `.name` on it crashes for an unknown id. Finding.

**Line B**

```ts
const ids = orders.map((o) => o.id).sort();
```

| Q | Answer |
| --- | --- |
| 1 | declaration |
| 2 | a chain: `map` then `sort` |
| 3 | object (array of numbers) |
| 4 | synchronous; no ticket |
| 5 | an array, never `undefined`; can be empty |
| 6 | `map` made a new array; `sort` mutates that new one, not `orders`; safe |
| 7 | kept in `ids` |
| note | `ids` holds: a new number[] sorted as strings (no comparator): `[1, 10, 9]` |

Finding if numeric order was required: `.sort((a, b) => a - b)`.

**Line C**

```ts
const data = res.json();
```

| Q | Answer |
| --- | --- |
| 1 | declaration |
| 2 | a call: `res.json()` |
| 3 | object: a Promise |
| 4 | `res.json()` returns a Promise; there is no `await`; `data` holds the ticket |
| 5 | not `undefined`, but not the body either |
| 6 | new Promise object; not shared |
| 7 | kept, but as a ticket |
| note | `data` holds: `Promise<any>`, a ticket, not awaited |

Next line `data.user`: `undefined`. Finding: missing `await`.

**Line D**

```ts
const opts = { ...defaults, ...input };
```

| Q | Answer |
| --- | --- |
| 1 | declaration |
| 2 | a literal with two spreads |
| 3 | object |
| 4 | no call; not a ticket |
| 5 | not `undefined`; individual keys may be |
| 6 | new address for `opts`; shallow: any nested object in `defaults` or `input` is shared; later keys win, so `input` overrides `defaults` (correct order) |
| 7 | kept |
| note | `opts` holds: a new object, input over defaults; `opts.nested` shared |

**Line E**

```ts
if (order.status = "paid") total += order.amount;
```

| Q | Answer |
| --- | --- |
| 1 | control, containing an assignment |
| 2 | the condition is an assignment expression; its value is `"paid"` |
| 3 | primitive string |
| 4 | no call |
| 5 | `"paid"` is truthy, always |
| 6 | the assignment mutates `order`, which is an element of the caller's array |
| 7 | the condition's value is used; it is always true |
| note | `order.status` is now `"paid"` for every order; branch always runs |

Finding: `=` for `===`; corrupts input and counts every order.

**Line F**

```ts
cache.set(key, await load(key));
```

| Q | Answer |
| --- | --- |
| 1 | expression statement |
| 2 | a call `cache.set` whose second argument is `await load(key)` |
| 3 | `set` returns the Map (object); the awaited value is whatever `load` resolves to |
| 4 | `load` is awaited here; `set` is synchronous |
| 5 | `key` could be `undefined` if it came from a header; then every keyless caller shares one entry |
| 6 | `cache` is shared module state; the `await` is a yield point: between the `has` check on the previous line and this `set`, another request can run the same miss |
| 7 | the mutation is the effect |
| note | `cache` now holds `key -> value`; race on concurrent misses; grows if keys are unbounded |

# "Released or not"

No line releases anything directly. A value stays alive while any label, array slot, Map entry, closure or timer points at it, and is reclaimed when the last one lets go. So the release question is Q6 run once at the end of each function, not per line:

1. Which labels go out of scope when the function returns? Their values are released, unless something else still points at them.
2. Which values were stored into something that outlives the function: a module-level `Map` or array, a cache, a listener, a `setInterval` closure, a returned object? Those are not released.
3. For each of those: who removes it later, and when? If nobody, it grows forever.

# The seven in one line each

1. **Kind:** declaration, assignment, expression, control, or type-only?
2. **Source:** literal, call, property read, operator, `await`, or destructuring?
3. **Primitive or object?**
4. **Ticket or value?** (calls only) Promise-returning, and awaited?
5. **Can it be nothing?** `undefined`/`null` possible, and checked before the next `.`?
6. **Who else points here?** (objects only) new address or alias; mutated; who else holds it?
7. **Was the result kept?** assigned, returned, awaited, passed, used, or dropped?

Then the note: *`label` holds: value, shared/own, nothing-possible, ticket/value.*
