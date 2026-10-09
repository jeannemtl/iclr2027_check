---
title: "Line Drill Deck"
subtitle: "Sixty single lines with the seven answers and the note — cover the answers, say them, uncover"
date: "October 2026"
---

**How to drill.** Cover everything below the code line. Say, out loud and in order: Kind · Source · Prim/Obj · Ticket? · Nothing? · Who else? · Kept? · then the note. Uncover and compare. Under a minute per line is the target. Assume the obvious context (`users: User[]`, `orders: Order[]`, `req` is an Express request, `cache` is a module-level `Map`, `getUser`/`save`/`load` are `async`).

# A. Declarations and literals

**1.** `const count = 0;`

| Kind | declaration (`const`) |
| --- | --- |
| Source | number literal |
| Prim/Obj | primitive |
| Ticket? | no call |
| Nothing? | no |
| Who else? | n/a (primitive) |
| Kept? | yes, in `count` |
| Note | `count` holds 0, a value; label fixed, but `count` is falsy |

**2.** `const user = { id: 1, name: "Ann" };`

| Kind | declaration |
| --- | --- |
| Source | object literal |
| Prim/Obj | object |
| Ticket? | no call |
| Nothing? | no |
| Who else? | new address; own |
| Kept? | yes |
| Note | `user` holds a new object; `user.name = "x"` is legal under `const` |

**3.** `const ids: number[] = [];`

| Kind | declaration with type |
| --- | --- |
| Source | array literal |
| Prim/Obj | object |
| Ticket? | no |
| Nothing? | no; empty is not nothing, and `[]` is truthy |
| Who else? | new; own |
| Kept? | yes |
| Note | `ids` holds a new empty array; `if (!ids)` never fires; use `ids.length === 0` |

**4.** `let total;`

| Kind | declaration, no value |
| --- | --- |
| Source | none |
| Prim/Obj | primitive (`undefined`) |
| Ticket? | no |
| Nothing? | yes, until assigned |
| Who else? | n/a |
| Kept? | n/a |
| Note | `total` holds `undefined`; type is `any` unless annotated; `total += 1` gives `NaN` |

**5.** `const { id, email } = user;`

| Kind | declaration, destructuring |
| --- | --- |
| Source | property reads `user.id`, `user.email` |
| Prim/Obj | whatever those are (likely primitives) |
| Ticket? | no |
| Nothing? | yes if either key is optional or absent on `user` |
| Who else? | if a value is an object, shared with `user` |
| Kept? | yes, two labels |
| Note | `id`, `email` hold the field values; `email` may be `undefined` if `email?:` |

**6.** `const [first, ...rest] = items;`

| Kind | declaration, array destructuring |
| --- | --- |
| Source | `items[0]` and a new array of the rest |
| Prim/Obj | `first` is an element (shared); `rest` is a new array |
| Ticket? | no |
| Nothing? | `first` is `undefined` if `items` is empty |
| Who else? | `first` shared with `items[0]`; `rest` own but its elements shared |
| Kept? | yes |
| Note | `first` holds `items[0]` or `undefined`; `rest` holds a new array |

**7.** `const opts = { ...DEFAULTS, ...input };`

| Kind | declaration |
| --- | --- |
| Source | object literal with two spreads |
| Prim/Obj | object |
| Ticket? | no |
| Nothing? | no; individual keys may be |
| Who else? | new outer object; nested objects shared with `DEFAULTS`/`input`; `input` keys win (correct order) |
| Kept? | yes |
| Note | `opts` holds a new object, input over defaults, shallow |

**8.** `const opts = { ...input, ...DEFAULTS };`

| Kind | declaration |
| --- | --- |
| Source | literal with two spreads |
| Prim/Obj | object |
| Ticket? | no |
| Nothing? | no |
| Who else? | new; shallow; `DEFAULTS` keys win, so user input is discarded |
| Kept? | yes |
| Note | `opts` holds defaults overriding input: BUG, order reversed |

**9.** `const copy = original;`

| Kind | declaration |
| --- | --- |
| Source | another label |
| Prim/Obj | object (assume) |
| Ticket? | no |
| Nothing? | if `original` can be |
| Who else? | ALIAS of `original`; nothing copied |
| Kept? | yes |
| Note | `copy` holds the same object as `original`; mutating `copy` mutates `original` |

**10.** `const copy = { ...original };`

| Kind | declaration |
| --- | --- |
| Source | spread literal |
| Prim/Obj | object |
| Ticket? | no |
| Nothing? | no |
| Who else? | new outer; `copy.inner` shared with `original.inner` |
| Kept? | yes |
| Note | `copy` holds a shallow copy; safe for top-level keys only |

**11.** `const f = (x: number) => x * 2;`

| Kind | declaration of a function |
| --- | --- |
| Source | arrow literal, expression body |
| Prim/Obj | object (function) |
| Ticket? | not async |
| Nothing? | no |
| Who else? | own |
| Kept? | yes |
| Note | `f` holds a function that returns `x * 2`; `f(3)` is 6 |

**12.** `const f = (x: number) => { x * 2 };`

| Kind | declaration of a function |
| --- | --- |
| Source | arrow literal, block body, no `return` |
| Prim/Obj | function |
| Ticket? | no |
| Nothing? | `f(3)` returns `undefined` |
| Who else? | own |
| Kept? | yes |
| Note | `f` holds a function that returns `undefined`: BUG, braces without return |

**13.** `const f = async (x: number) => x * 2;`

| Kind | declaration |
| --- | --- |
| Source | async arrow |
| Prim/Obj | function |
| Ticket? | calling it returns `Promise<number>` |
| Nothing? | no |
| Who else? | own |
| Kept? | yes |
| Note | `f(3)` is a ticket for 6; `await f(3)` is 6 |

**14.** `interface User { id: number; email?: string }`

| Kind | type-only |
| --- | --- |
| Source | n/a |
| Prim/Obj | n/a |
| Ticket? | n/a |
| Nothing? | the claim: `email` may be absent |
| Who else? | n/a |
| Kept? | n/a |
| Note | runs nothing; every `user.email` downstream is `string \| undefined` |

**15.** `const key = req.headers["x-api-key"] as string;`

| Kind | declaration with a cast |
| --- | --- |
| Source | property read from a request |
| Prim/Obj | primitive (or `string[]`, or `undefined`) |
| Ticket? | no |
| Nothing? | YES; header may be absent; the `as` hides it |
| Who else? | n/a |
| Kept? | yes |
| Note | `key` holds a string OR `undefined` OR an array; the cast is a lie; next use must check |

# B. Assignments and mutations

**16.** `total = total + order.amount;`

| Kind | reassignment |
| --- | --- |
| Source | arithmetic |
| Prim/Obj | primitive number |
| Ticket? | no |
| Nothing? | `NaN` if `order.amount` is `undefined` or a non-numeric string |
| Who else? | n/a |
| Kept? | yes |
| Note | `total` holds the sum; poisoned to `NaN` by one bad amount; floats drift for money |

**17.** `user.name = name.trim();`

| Kind | property set (mutation) |
| --- | --- |
| Source | string method (returns new) |
| Prim/Obj | string stored into an object |
| Ticket? | no |
| Nothing? | `name` must not be `undefined` or `.trim` crashes |
| Who else? | mutates `user`; every alias of `user` sees the new name |
| Kept? | yes, the mutation |
| Note | `user.name` is now the trimmed string; `user` shared with whoever passed it |

**18.** `orders.sort((a, b) => a.total - b.total);`

| Kind | expression statement, mutating call |
| --- | --- |
| Source | `sort` with numeric comparator |
| Prim/Obj | object (array) |
| Ticket? | no |
| Nothing? | no |
| Who else? | MUTATES `orders` in place; if `orders` is a parameter, the caller's array is reordered |
| Kept? | the mutation is the effect |
| Note | `orders` is now sorted ascending by total; finding if the input must not change |

**19.** `const sorted = orders.sort();`

| Kind | declaration |
| --- | --- |
| Source | `sort` with no comparator |
| Prim/Obj | array |
| Ticket? | no |
| Nothing? | no |
| Who else? | `sorted === orders`; not a copy; and objects sort by `"[object Object]"` |
| Kept? | kept, but misleading |
| Note | `sorted` holds the same array as `orders`, both reordered meaninglessly: BUG twice |

**20.** `const sorted = [...orders].sort((a, b) => a.total - b.total);`

| Kind | declaration |
| --- | --- |
| Source | spread copy, then sort |
| Prim/Obj | array |
| Ticket? | no |
| Nothing? | no |
| Who else? | new array; `orders` untouched; elements still shared |
| Kept? | yes |
| Note | `sorted` holds a new sorted array; correct pattern |

**21.** `arr.length = 0;`

| Kind | assignment to a property |
| --- | --- |
| Source | literal 0 |
| Prim/Obj | mutates an array |
| Ticket? | no |
| Nothing? | no |
| Who else? | every alias of `arr` is now empty |
| Kept? | the mutation |
| Note | `arr` emptied in place |

**22.** `delete cache[key];`

| Kind | expression statement (mutation) |
| --- | --- |
| Source | `delete` operator |
| Prim/Obj | mutates an object |
| Ticket? | no |
| Nothing? | if `key` is `undefined`, deletes the key `"undefined"` |
| Who else? | shared module state |
| Kept? | the mutation |
| Note | key removed; if `cache` is a `Map`, this does nothing and `cache.delete(key)` was meant |

**23.** `count ??= 0;`

| Kind | logical assignment |
| --- | --- |
| Source | `??=` |
| Prim/Obj | primitive |
| Ticket? | no |
| Nothing? | after this line, no |
| Who else? | n/a |
| Kept? | yes |
| Note | `count` is 0 only if it was `null`/`undefined`; an existing 0 stays 0 (correct, unlike `\|\|=`) |

**24.** `if (order.status = "paid") paid.push(order);`

| Kind | control with an assignment inside the condition |
| --- | --- |
| Source | assignment expression; value `"paid"` |
| Prim/Obj | primitive |
| Ticket? | no |
| Nothing? | `"paid"` is truthy; branch always runs |
| Who else? | mutates `order`, an element of the caller's array |
| Kept? | the condition is used, but always true |
| Note | every order's status becomes `"paid"` and every order is pushed: BUG, `=` for `===` |

# C. Reads and lookups

**25.** `const user = users.find((u) => u.id === id);`

| Kind | declaration |
| --- | --- |
| Source | `find` |
| Prim/Obj | object or `undefined` |
| Ticket? | no |
| Nothing? | YES on no match; also if `id` is a string and `u.id` a number, always undefined |
| Who else? | shared with the element inside `users` |
| Kept? | yes |
| Note | `user` holds an element of `users` or `undefined`; next `.` must check |

**26.** `const name = user!.name;`

| Kind | declaration with non-null assertion |
| --- | --- |
| Source | property read through `!` |
| Prim/Obj | primitive |
| Ticket? | no |
| Nothing? | the `!` claims no; nothing checks; crashes if `user` is undefined |
| Who else? | n/a |
| Kept? | yes |
| Note | `name` holds the string if `user` exists; the `!` is an unverified claim |

**27.** `const name = user?.profile?.name ?? "anon";`

| Kind | declaration |
| --- | --- |
| Source | optional chain with nullish fallback |
| Prim/Obj | primitive |
| Ticket? | no |
| Nothing? | no; `"anon"` fills every hole |
| Who else? | n/a |
| Kept? | yes |
| Note | `name` holds a string, always; correct defensive read |

**28.** `const list = index.get(tag);`

| Kind | declaration |
| --- | --- |
| Source | `Map.get` |
| Prim/Obj | object (array) or `undefined` |
| Ticket? | no |
| Nothing? | YES when the tag is new |
| Who else? | shared with the value inside the map |
| Kept? | yes |
| Note | `list` holds the map's array or `undefined`; `list.push` crashes on a new tag |

**29.** `index.get(tag).push(doc);`

| Kind | expression statement |
| --- | --- |
| Source | `get` then `push` |
| Prim/Obj | array inside the map |
| Ticket? | no |
| Nothing? | `get` is `undefined` for a new tag; `.push` throws |
| Who else? | mutates the map's array |
| Kept? | the mutation |
| Note | crashes on first new tag: BUG; use `?? []` and `set` |

**30.** `const last = arr[arr.length - 1];`

| Kind | declaration |
| --- | --- |
| Source | index read |
| Prim/Obj | element (shared) or `undefined` |
| Ticket? | no |
| Nothing? | yes if `arr` is empty (`arr[-1]`) |
| Who else? | shared with the element |
| Kept? | yes |
| Note | `last` holds the last element or `undefined` |

**31.** `const size = Number(req.query.size);`

| Kind | declaration |
| --- | --- |
| Source | conversion call |
| Prim/Obj | primitive number |
| Ticket? | no |
| Nothing? | never `undefined`; `NaN` if absent or non-numeric; `0` if `"0"` |
| Who else? | n/a |
| Kept? | yes |
| Note | `size` holds a number, possibly `NaN`; a range check alone will not reject `NaN` |

**32.** `const size = Number(req.query.size) || 20;`

| Kind | declaration |
| --- | --- |
| Source | conversion with `\|\|` fallback |
| Prim/Obj | number |
| Ticket? | no |
| Nothing? | no; but `0` and `NaN` both become 20 |
| Who else? | n/a |
| Kept? | yes |
| Note | `size` holds 20 for `?size=0` (wrong) and for `?size=abc` (silently); negative passes |

**33.** `const orgId = req.query.orgId ?? claims.orgId;`

| Kind | declaration |
| --- | --- |
| Source | `??` between request input and token claim |
| Prim/Obj | primitive |
| Ticket? | no |
| Nothing? | no if claims has it |
| Who else? | n/a |
| Kept? | yes |
| Note | `orgId` holds whatever the CALLER sent, overriding the token: AUTH BYPASS; use `claims.orgId` only |

**34.** `for (const i in items) total += items[i + 1];`

| Kind | control, `for...in` on an array |
| --- | --- |
| Source | index keys as strings |
| Prim/Obj | `i` is a string |
| Ticket? | no |
| Nothing? | `items["01"]` is `undefined` |
| Who else? | n/a |
| Kept? | `total` becomes `NaN` |
| Note | `i` holds `"0"`, `"1"`; `i + 1` is `"01"`: BUG, use `for...of` or a counting loop |

**35.** `for (const [k, v] of Object.entries(counts)) {`

| Kind | control, `for...of` with destructuring |
| --- | --- |
| Source | `Object.entries` (new array of pairs) |
| Prim/Obj | `k` string, `v` whatever the values are |
| Ticket? | no |
| Nothing? | no |
| Who else? | `v` shared with `counts[k]` if an object |
| Kept? | n/a |
| Note | `k`, `v` hold each key and value; the Python `d.items()` form |

# D. Calls, sync

**36.** `const paid = orders.filter((o) => o.status === "paid");`

| Kind | declaration |
| --- | --- |
| Source | `filter` |
| Prim/Obj | new array |
| Ticket? | no |
| Nothing? | no; possibly empty |
| Who else? | new array; elements shared with `orders` |
| Kept? | yes |
| Note | `paid` holds a new array of the same order objects |

**37.** `orders.filter((o) => o.status === "paid");`

| Kind | expression statement |
| --- | --- |
| Source | `filter` |
| Prim/Obj | new array |
| Ticket? | no |
| Nothing? | no |
| Who else? | nothing mutated |
| Kept? | NO; dropped |
| Note | dead line; nothing happened |

**38.** `const amounts = orders.map((o) => { o.amount });`

| Kind | declaration |
| --- | --- |
| Source | `map` with block body, no `return` |
| Prim/Obj | array of `undefined` |
| Ticket? | no |
| Nothing? | every element is `undefined` |
| Who else? | new array |
| Kept? | yes, but useless |
| Note | `amounts` holds `[undefined, ...]`: BUG, braces without return |

**39.** `const total = amounts.reduce((a, b) => a + b);`

| Kind | declaration |
| --- | --- |
| Source | `reduce` without initial value |
| Prim/Obj | number |
| Ticket? | no |
| Nothing? | THROWS on empty `amounts` |
| Who else? | n/a |
| Kept? | yes |
| Note | `total` holds the sum, or a TypeError on `[]`; add `, 0` |

**40.** `const n = arr.push(x);`

| Kind | declaration |
| --- | --- |
| Source | `push` (mutating; returns length) |
| Prim/Obj | number |
| Ticket? | no |
| Nothing? | no |
| Who else? | `arr` mutated |
| Kept? | yes, but it is the length, not the array |
| Note | `n` holds the new length; `arr` has `x` appended |

**41.** `name.trim();`

| Kind | expression statement |
| --- | --- |
| Source | string method |
| Prim/Obj | new string |
| Ticket? | no |
| Nothing? | n/a |
| Who else? | nothing mutated (strings immutable) |
| Kept? | NO |
| Note | dead line; `name` unchanged |

**42.** `const data = JSON.parse(body);`

| Kind | declaration |
| --- | --- |
| Source | `JSON.parse` (sync) |
| Prim/Obj | anything; typed `any` |
| Ticket? | no |
| Nothing? | `null` if body is `"null"`; throws if malformed |
| Who else? | new |
| Kept? | yes |
| Note | `data` holds an unvalidated value of unknown shape; needs `try` and a runtime check |

**43.** `const data = JSON.parse(body) as Config;`

| Kind | declaration with cast |
| --- | --- |
| Source | `JSON.parse` |
| Prim/Obj | any |
| Ticket? | no |
| Nothing? | same as 42; the cast changes nothing |
| Who else? | new |
| Kept? | yes |
| Note | `data` holds whatever the client sent, labeled `Config` with no check: TYPE HOLE |

**44.** `const ok = users.includes(user);`

| Kind | declaration |
| --- | --- |
| Source | `includes` on objects |
| Prim/Obj | boolean |
| Ticket? | no |
| Nothing? | no |
| Who else? | n/a |
| Kept? | yes |
| Note | `ok` is `true` only if that exact object (same address) is in `users`; a fresh `{ id: 1 }` is never found |

**45.** `const d = new Date(order.createdAt);`

| Kind | declaration |
| --- | --- |
| Source | constructor |
| Prim/Obj | object (Date), mutable |
| Ticket? | no |
| Nothing? | `Invalid Date` if the input is garbage; `d.getTime()` is `NaN` |
| Who else? | new |
| Kept? | yes |
| Note | `d` holds a Date; compare with `.getTime()`, never `===` |

# E. Calls, async

**46.** `const user = getUser(id);`

| Kind | declaration |
| --- | --- |
| Source | async call |
| Prim/Obj | object: a Promise |
| Ticket? | TICKET; no `await` |
| Nothing? | `user.name` is `undefined` |
| Who else? | new Promise |
| Kept? | kept, as a ticket |
| Note | `user` holds `Promise<User>`, not awaited: BUG |

**47.** `const user = await getUser(id);`

| Kind | declaration |
| --- | --- |
| Source | awaited async call |
| Prim/Obj | object (User) |
| Ticket? | unwrapped |
| Nothing? | only if `getUser` can resolve to `null`/`undefined` |
| Who else? | depends on `getUser`; if it returns a cached object, shared |
| Kept? | yes |
| Note | `user` holds a User; this line is a yield point |

**48.** `save(data);`

| Kind | expression statement |
| --- | --- |
| Source | async call |
| Prim/Obj | Promise |
| Ticket? | ticket, dropped |
| Nothing? | n/a |
| Who else? | n/a |
| Kept? | NO |
| Note | fire-and-forget; rejection unhandled; function continues before save finishes |

**49.** `const data = res.json();`

| Kind | declaration |
| --- | --- |
| Source | `res.json()` |
| Prim/Obj | Promise |
| Ticket? | ticket, not awaited |
| Nothing? | `data.user` is `undefined` |
| Who else? | new |
| Kept? | as a ticket |
| Note | `data` holds `Promise<any>`: BUG, missing `await` |

**50.** `const res = await fetch(url); const user = await res.json();`

| Kind | two declarations |
| --- | --- |
| Source | `fetch`, then `res.json()` |
| Prim/Obj | Response, then any |
| Ticket? | both awaited |
| Nothing? | `res.ok` unchecked: a 404 body is parsed as `user` |
| Who else? | new |
| Kept? | yes |
| Note | `user` holds the parsed body of ANY status; needs `if (!res.ok) throw` between them |

**51.** `const users = ids.map((id) => getUser(id));`

| Kind | declaration |
| --- | --- |
| Source | `map` with an async callback |
| Prim/Obj | array of Promises |
| Ticket? | an ARRAY of tickets |
| Nothing? | `users[0].name` is `undefined` |
| Who else? | new array |
| Kept? | yes, but as tickets |
| Note | `users` holds `Promise<User>[]`; needs `await Promise.all(...)` |

**52.** `const users = await Promise.all(ids.map((id) => getUser(id)));`

| Kind | declaration |
| --- | --- |
| Source | `Promise.all` over mapped Promises |
| Prim/Obj | array of Users |
| Ticket? | all unwrapped, in input order |
| Nothing? | rejects entirely on the first failure |
| Who else? | new array |
| Kept? | yes |
| Note | `users` holds `User[]`; parallel; correct |

**53.** `ids.forEach(async (id) => { await save(id); });`

| Kind | expression statement |
| --- | --- |
| Source | `forEach` with async callback |
| Prim/Obj | `forEach` returns `undefined` |
| Ticket? | each callback's Promise is dropped by `forEach` |
| Nothing? | n/a |
| Who else? | n/a |
| Kept? | NO; nothing waits |
| Note | the saves run detached; the function continues immediately: BUG |

**54.** `for (const id of ids) await save(id);`

| Kind | control |
| --- | --- |
| Source | awaited call per iteration |
| Prim/Obj | n/a |
| Ticket? | each awaited; sequential |
| Nothing? | n/a |
| Who else? | n/a |
| Kept? | the side effect |
| Note | saves run one at a time; correct if order matters, slow if not |

**55.** `try { save(data); } catch (e) { log(e); }`

| Kind | control, `try` |
| --- | --- |
| Source | async call inside, not awaited |
| Prim/Obj | Promise dropped |
| Ticket? | not awaited inside the `try` |
| Nothing? | n/a |
| Who else? | n/a |
| Kept? | NO |
| Note | the `try` ends before the Promise settles; `catch` never runs: BUG, `await save(data)` |

**56.** `return fetch(url);` (inside a `try` in a non-async function)

| Kind | control, `return` |
| --- | --- |
| Source | `fetch` (Promise) |
| Prim/Obj | Promise |
| Ticket? | handed to the caller un-awaited |
| Nothing? | n/a |
| Who else? | n/a |
| Kept? | returned |
| Note | the Promise leaves the `try` pending; this function's `catch` is dead; caller must handle |

**57.** `return await fetch(url);` (inside a `try` in an async function)

| Kind | control, `return` with `await` |
| --- | --- |
| Source | `fetch`, awaited |
| Prim/Obj | Response |
| Ticket? | unwrapped here |
| Nothing? | n/a |
| Who else? | n/a |
| Kept? | returned |
| Note | a rejection is thrown inside this `try`; `catch` runs; the one place `return await` matters |

**58.** `const n = counts.get(k) ?? 0; await db.save(k); counts.set(k, n + 1);`

| Kind | three statements: read, await, write |
| --- | --- |
| Source | `Map.get`, async call, `Map.set` |
| Prim/Obj | number; shared Map |
| Ticket? | `save` awaited |
| Nothing? | `get` miss handled by `?? 0` |
| Who else? | `counts` is shared; another request runs at the `await` |
| Kept? | the write |
| Note | read-await-write on shared state: RACE; concurrent requests lose increments |

**59.** `if (!cache.has(k)) cache.set(k, await load(k));`

| Kind | control with an awaited call inside |
| --- | --- |
| Source | `has`, then `load` awaited, then `set` |
| Prim/Obj | shared Map |
| Ticket? | `load` awaited |
| Nothing? | n/a |
| Who else? | `cache` shared; every concurrent miss passes `has` before any `set` |
| Kept? | the write |
| Note | check-then-set across an `await`: all concurrent misses call `load`; store the Promise instead |

**60.** `setInterval(sweep, 60_000);`

| Kind | expression statement |
| --- | --- |
| Source | timer call |
| Prim/Obj | returns a timer id (number/object), dropped |
| Ticket? | not a Promise |
| Nothing? | n/a |
| Who else? | the timer holds `sweep` and its closure forever |
| Kept? | id dropped, so it can never be cleared |
| Note | runs every minute, keeps the process alive, cannot be cancelled: needs `.unref()` or a stored id |

# Answer key in one table

| # | Verdict | Which Q caught it |
| --- | --- | --- |
| 1–3, 5–7, 10, 11, 13, 14, 20, 23, 27, 35, 36, 40, 44, 45, 47, 52, 54, 57 | fine (with the stated caveat) | |
| 4 | `undefined` until assigned | Q5 |
| 8 | spread order reversed | Q6 |
| 9 | alias, not copy | Q6 |
| 12 | braces without return | Q5/Q7 |
| 15 | cast hides `undefined` | Q5 |
| 16 | `NaN` poisoning; float money | Q5 |
| 17 | mutates shared `user` | Q6 |
| 18 | mutates caller's array | Q6 |
| 19 | `sort()` not a copy, string order | Q6/Q7 |
| 21, 22 | mutation reaches all aliases; `delete` on a Map does nothing | Q6 |
| 24 | `=` in condition | Q2/Q5 |
| 25, 28, 30 | can be `undefined` | Q5 |
| 26 | `!` unverified | Q5 |
| 29 | `get().push` crash | Q5 |
| 31, 32 | `NaN`; `\|\|` eats 0 | Q5 |
| 33 | auth bypass via `??` | Q2 (source is the caller) |
| 34 | `for...in` string index | Q2/Q5 |
| 37, 41 | result dropped | Q7 |
| 38 | braces without return | Q5 |
| 39 | `reduce` on empty throws | Q5 |
| 42, 43 | unvalidated parse; cast | Q5 |
| 46, 49, 51 | ticket not awaited | Q4 |
| 48, 53 | fire-and-forget | Q4/Q7 |
| 50 | `res.ok` unchecked | Q5 |
| 55, 56 | `try` without `await` inside | Q4 |
| 58, 59 | race across `await` | Q6 |
| 60 | timer never cleared | Q6/Q7 |
