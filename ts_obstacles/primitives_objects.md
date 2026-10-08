---
title: "Primitives and Objects"
subtitle: "The seven primitives, every object kind you will meet, and the four rules that split them"
date: "October 2026"
---

**The split.** Every value in TypeScript is either a **primitive** or an **object**. Primitives are atoms: a single value with no parts to reach into. Objects are containers: they have keys, elements or internal state that can be edited. Which side a value is on decides whether it can be mutated, whether two labels can alias it, how `===` compares it, and whether it has its own keys.

# The seven primitives

| Primitive | Literal | `typeof` | Notes |
| --- | --- | --- | --- |
| `string` | `"abc"`, `'abc'`, `` `a ${x}` `` | `"string"` | immutable; every method returns a new string |
| `number` | `42`, `3.5`, `-0`, `NaN`, `Infinity` | `"number"` | one type for integers and floats; `NaN` is a number |
| `boolean` | `true`, `false` | `"boolean"` | |
| `undefined` | `undefined` | `"undefined"` | never assigned; missing key; no `return` |
| `null` | `null` | `"object"` | deliberately empty; the `typeof` result is a historical wart |
| `bigint` | `9007199254740993n` | `"bigint"` | integers beyond 2^53; cannot mix with `number` in arithmetic |
| `symbol` | `Symbol("id")` | `"symbol"` | unique keys; rare in application code |

Python equivalents: `str`, `int`/`float`, `bool`, `None` (for both `null` and `undefined`), `int` (for `bigint`); no `symbol`.

**Four rules that hold for every primitive**

1. **Immutable.** No operation edits a primitive in place. `s.toUpperCase()` returns a new string; `s[0] = "x"` is silently ignored; `n++` reassigns `n` to a new number.
2. **Compared by value.** `"a" === "a"` is `true`; `5 === 5` is `true`. The one exception is `NaN === NaN`, which is `false`; use `Number.isNaN`.
3. **Copied on assignment.** `let y = x` gives `y` its own value; nothing done to `y` affects `x`. Passing a primitive to a function cannot change the caller's variable.
4. **No own keys.** `n.foo = 1` is silently ignored. `"abc".length` and `"abc".toUpperCase()` work because the engine wraps the primitive in a temporary object for the call, then discards it.

# The objects

Everything that is not one of the seven above. All objects share the opposite four rules: mutable (unless frozen), compared by identity, aliased on assignment, and able to carry keys.

**Core containers**

| Object | Literal / constructor | `typeof` | Python | Notes |
| --- | --- | --- | --- | --- |
| plain object | `{ a: 1 }`, `new Object()` | `"object"` | `dict` | string keys; inherits from `Object.prototype` |
| array | `[1, 2]`, `new Array(3)`, `Array.from(x)` | `"object"` | `list` | `Array.isArray(x)` is the only reliable check |
| `Map` | `new Map([["k", 1]])` | `"object"` | `dict` | any key type; no prototype keys; insertion order |
| `Set` | `new Set([1, 2])` | `"object"` | `set` | unique values |
| `WeakMap`, `WeakSet` | `new WeakMap()` | `"object"` | | keys are objects, held weakly; not iterable |
| `Object.create(null)` | | `"object"` | | plain object with no prototype; safe for user keys |

**Functions (objects that can be called)**

| Object | Literal | `typeof` | Notes |
| --- | --- | --- | --- |
| function | `function f() {}`, `() => {}`, `async () => {}` | `"function"` | the only object with `typeof` other than `"object"`; can have properties |
| class | `class A {}` | `"function"` | a constructor function; `new A()` makes an instance |
| generator | `function* g() {}` | `"function"` | |

**Built-in wrappers and values**

| Object | Constructor | Notes |
| --- | --- | --- |
| `Date` | `new Date()`, `new Date(0)` | mutable (`setDate`); compare with `.getTime()`; `Date.now()` is a primitive number |
| `RegExp` | `/ab+/g`, `new RegExp("ab+")` | with the `g` flag it carries `lastIndex` state between calls |
| `Error` and subclasses | `new Error("m")`, `new TypeError()` | `.message`, `.stack`, `.cause`; `catch (e)` gives `unknown` |
| `Promise` | `new Promise(...)`, any `async` call | a ticket; unwrap with `await` |
| class instance | `new User()` | has the class's methods via its prototype |
| `String`, `Number`, `Boolean` objects | `new String("a")` | wrapper OBJECTS, never used deliberately; `new String("a") === "a"` is `false` |

**Binary and typed data**

| Object | Constructor | Notes |
| --- | --- | --- |
| `ArrayBuffer` | `new ArrayBuffer(8)` | raw bytes |
| typed arrays | `new Uint8Array(4)`, `Float64Array` | fixed-type numeric arrays |
| `Buffer` (Node) | `Buffer.from("abc")` | Node's byte array |
| `Blob`, `File` (browser) | | |

**Iteration and async helpers**

| Object | Notes |
| --- | --- |
| iterator / generator object | what `function*` returns; `.next()` |
| `AbortController`, `AbortSignal` | cancel a `fetch` |
| `URL`, `URLSearchParams` | parsed URL; mutable |
| `Headers`, `Request`, `Response` | the `fetch` family |
| `FormData` | |

**Framework objects you will meet in handlers**

| Object | Notes |
| --- | --- |
| Express `req` | `req.params`, `req.query`, `req.body`, `req.headers` are all objects; their values are strings, arrays or `any` |
| Express `res` | `res.status()`, `res.json()`, `res.send()` are methods; calling them does not end the function |
| database client / pool | every query method returns a Promise |
| `EventEmitter` | `.on`, `.off`, `.emit`; listeners never removed are leaks |

# Telling them apart at runtime

| Check | Primitive | Object |
| --- | --- | --- |
| `typeof x` | `"string"`, `"number"`, `"boolean"`, `"undefined"`, `"bigint"`, `"symbol"` | `"object"` or `"function"` (and `null` wrongly says `"object"`) |
| `x === null` | catches `null` | |
| `Array.isArray(x)` | | `true` for arrays only |
| `x instanceof Date` / `Map` / `Error` / `MyClass` | | `true` when built by that constructor |
| `Object(x) === x` | `false` | `true` |

A reliable "is this a primitive" test: `x === null || (typeof x !== "object" && typeof x !== "function")`.

# The four rules side by side

| Rule | Primitive | Object |
| --- | --- | --- |
| Can be edited in place? | never | yes (unless `Object.freeze`, and then only one level) |
| `===` compares | the value | the address (identity) |
| `let y = x` gives | an independent value | a second label on the same thing |
| Own keys? | none; `x.foo = 1` ignored | yes; `x.foo = 1` adds a key |
| Passed to a function | the function cannot change the caller's variable | the function can mutate the caller's object |
| Review question | was the method's result stored? | who else is holding this? which methods mutate? |

# Where the split shows up in the sheets

| Topic | Primitive side | Object side |
| --- | --- | --- |
| Mutability (its own sheet) | every method returns new; call-then-assign | mutate vs return-new tables |
| Memory model | observably copied | arrows shared |
| Equality (Behaviors 8) | `===` on values | `===` on identity; compare contents by hand |
| Truthiness (Obstacles note B) | `0`, `""`, `NaN` falsy | every object truthy, including `[]` and `{}` |
| Map keys (Obstacles note J) | `1` and `"1"` are different keys | an object key is matched by identity only |
| `undefined` / `null` | both are primitives | following an arrow to them is the crash |

**One sentence to keep.** Seven primitives (string, number, boolean, undefined, null, bigint, symbol) are immutable, compared by value, copied on assignment and have no keys; everything else is an object and is the opposite on all four.
