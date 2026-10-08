---
title: "Mutable and Immutable"
subtitle: "Which values can be edited in place, which cannot, what each method does, and what to check in review"
date: "October 2026"
---

**The definition.** A value is **mutable** if its contents can be edited at its address while labels keep pointing at it. A value is **immutable** if its contents can never be edited; every "change" produces a new value at a new address, and the old one is untouched.

**Why it matters.** Mutable values can surprise you through another label (aliasing). Immutable values cannot, but their methods do nothing unless you store the result. Each kind has its own bug.

# 1. Which is which

| Kind | Values | Can be edited in place? |
| --- | --- | --- |
| immutable primitives | `string`, `number`, `boolean`, `bigint`, `symbol`, `null`, `undefined` | never |
| mutable objects | `{}` plain objects, `[]` arrays, `Map`, `Set`, `Date`, class instances, functions, `RegExp` with state | yes |
| frozen objects | `Object.freeze(o)` | no, shallow, silently ignored outside strict mode |
| `readonly` typed | `readonly number[]`, `Readonly<T>`, `as const` | compile-time only; the runtime object is still mutable |

Python parallel: `str`, `int`, `float`, `tuple`, `frozenset` immutable; `list`, `dict`, `set` mutable. Same split, same reasons. One difference: Python throws on `s[0] = "x"`; TypeScript silently ignores it.

# 2. Immutable values: every change is a new value

No string, number or boolean method edits the original. Each returns a new value, and if nothing stores it, the call did nothing.

```ts
let s = " Ann ";
s.trim();                 // builds "Ann"; nobody stores it; s is still " Ann "   ✗ no effect
s = s.trim();             // s now points at "Ann"                                ✓
const t = s.toUpperCase();   // t is "ANN"; s still "Ann"                           ✓ both kept

s[0] = "x";               // silently ignored; s unchanged
s.length = 0;             // silently ignored

let n = 5;
n + 1;                    // computes 6; nobody stores it; n is still 5
n = n + 1;                // n is 6
n++;                      // n is 7 (shorthand for n = n + 1)
```

**Every string method returns new:** `trim`, `toUpperCase`, `toLowerCase`, `replace`, `replaceAll`, `slice`, `substring`, `split`, `padStart`, `padEnd`, `concat`, `repeat`, `at`, `charAt`, `normalize`. There is no in-place string method at all.

**Consequences.**

- The pattern is always *call, then assign*: `x = x.method()` or `const y = x.method()`.
- `x = x.method()` is a reassignment, so `x` must be `let`; under `const`, use a new name.
- Two labels on the same string can never see each other change, so aliasing is impossible for primitives; passing a string to a function cannot change the caller's string.
- "Build a new one" is how you change a character: `"x" + s.slice(1)`.

**Review question.** Any string or number method on its own line with nothing assigned? That line does nothing.

# 3. Mutable values: some methods edit in place, some return new

Arrays and objects can be edited at their address. Some methods do that; others leave the original alone and return a fresh value. You must know which is which for each call.

**Array methods that MUTATE (edit the array in place)**

| Method | Does | Returns | Trap |
| --- | --- | --- | --- |
| `push(x)` | appends | the new length | `const a = arr.push(1)` holds a number |
| `pop()` | removes last | the removed item | |
| `shift()` | removes first | the removed item | O(n) |
| `unshift(x)` | prepends | the new length | |
| `splice(i, n, ...items)` | removes/inserts at `i` | array of removed items | |
| `sort(cmp)` | reorders | the SAME array | `const s = arr.sort()` is not a copy |
| `reverse()` | reverses | the SAME array | same |
| `fill(v)` | overwrites every slot | the SAME array | |
| `copyWithin` | copies within | the SAME array | |
| `arr[i] = v` | sets a slot | `v` | |
| `arr.length = 0` | empties | | all labels see it empty |
| `delete arr[i]` | leaves a hole | `true` | avoid |

**Array methods that DO NOT mutate (return something new; original untouched)**

| Method | Returns | Must store? |
| --- | --- | --- |
| `map(f)` | new array, same length | yes |
| `filter(p)` | new array, subset | yes |
| `slice(a, b)` | new array, copy of a range | yes |
| `concat(b)` | new array | yes |
| `flat()`, `flatMap(f)` | new array | yes |
| `toSorted(cmp)`, `toReversed()`, `toSpliced()`, `with(i, v)` | new array; the non-mutating twins of `sort`, `reverse`, `splice`, `arr[i] = v` | yes |
| `reduce(f, init)` | a value | yes |
| `find(p)`, `findIndex(p)`, `findLast(p)` | element / index / `undefined` | yes |
| `some(p)`, `every(p)`, `includes(x)`, `indexOf(x)` | boolean / index | yes |
| `join(sep)` | string | yes |
| `at(i)` | element | yes |
| `forEach(f)` | `undefined` | no; it is for side effects only |
| `[...arr]`, `Array.from(arr)` | new array (shallow copy) | yes |

**Object operations**

| Operation | Mutates? |
| --- | --- |
| `o.k = v`, `o[k] = v` | yes |
| `delete o.k` | yes |
| `Object.assign(o, src)` | yes, mutates `o` (the first argument) |
| `Object.assign({}, src)` | no; mutates the fresh `{}` |
| `{ ...o, k: v }` | no; new object |
| `Object.keys/values/entries(o)` | no; new arrays |
| `Object.freeze(o)` | makes `o` shallowly immutable; returns `o` |
| `structuredClone(o)` | no; deep copy |

**Map and Set**: `set`, `delete`, `clear`, `add` mutate and return the collection (or a boolean); `get`, `has`, `size`, iteration do not.

**Date**: `setFullYear`, `setMonth`, `setDate`, `setHours`, `setTime` mutate the date in place; `getTime`, `toISOString` do not. `const d = new Date(); d.setDate(1)` edits `d`.

# 4. The two opposite bugs

**Bug A: treating a non-mutating call as if it changed the original.**

```ts
orders.filter((o) => o.paid);        // new array built and dropped; orders unchanged
name.trim();                         // same
arr.map((x) => x * 2);               // same
```

Nothing happened. Fix: store the result.

**Bug B: treating a mutating call as if it made a copy.**

```ts
const sorted = ids.sort();           // ids is now sorted too; sorted IS ids
const rev = arr.reverse();           // arr is now reversed too
const removed = arr.splice(0, 2);    // arr lost two items
```

The original changed, and every label pointing at it sees the change. Fix: copy first (`[...ids].sort()`), or use the non-mutating twin (`ids.toSorted()`).

| You see | Ask | If wrong |
| --- | --- | --- |
| a method call on its own line | does this method return new? | Bug A: dead line |
| `const x = arr.method()` | does this method mutate `arr`? | Bug B: `x` and `arr` are the same thing, both changed |
| a method on a parameter | does it mutate? | Bug B on the caller's data |
| a method on a returned or cached value | does it mutate? | Bug B on shared state |

# 5. `const`, `readonly`, `Object.freeze`: what each actually prevents

| Written | Prevents | At | Does not prevent |
| --- | --- | --- | --- |
| `const a = [1]` | `a = [2]` (re-pointing the label) | compile and runtime | `a.push(2)`, `a[0] = 9` |
| `let a: readonly number[]` | `a.push`, `a[0] = 9` in TS code | compile time only | a JS caller or an `as any` mutating it |
| `Readonly<T>`, `readonly k: T` | assignment to those fields | compile time only | mutation through a non-readonly alias of the same object |
| `as const` | widening; makes literals readonly | compile time only | runtime mutation |
| `Object.freeze(o)` | `o.k = v`, `delete o.k`, `o.push` | runtime, shallow | `o.inner.k = v`; silently ignored outside strict mode, throws inside |
| `#field` | access from outside the class | runtime | mutation from inside |

So `const` is about the label; `readonly` is about the compiler; `Object.freeze` is about the runtime, one level deep. None of them makes a nested object immutable. True deep immutability needs a library or a discipline of never mutating.

# 6. Copying: how to get a mutable value you can change safely

| Written | Copies | Depth |
| --- | --- | --- |
| `[...a]`, `a.slice()`, `Array.from(a)` | the array | shallow |
| `{ ...o }` | the object | shallow |
| `new Map(m)`, `new Set(s)` | the collection | shallow |
| `a.map((x) => ({ ...x }))` | the array and one level of its objects | two levels |
| `structuredClone(o)` | everything | deep |
| `JSON.parse(JSON.stringify(o))` | everything plain; drops `undefined`, functions, `Map`, `Set`; `Date` becomes a string | deep-ish |

Shallow means the container is new but the things inside are the same objects. `const c = { ...o }; c.inner.x = 9` changes `o.inner.x`. `filter` and `map` return shallow copies: the elements are the original objects.

# 7. Aliasing: the mutable-only hazard

Two labels on one mutable value see each other's edits. This is never a problem for primitives and always a possible problem for objects.

```ts
const defaults = { retries: 3 };
const opts = defaults;           // alias
opts.retries = 5;                // defaults.retries is 5 for every later caller

const opts2 = { ...defaults };   // copy
opts2.retries = 5;               // defaults untouched
```

Where aliases come from: `b = a`; passing an object to a function; returning an internal array (`return this.items`); storing an object in a cache and also handing it out; `filter`/`map` results sharing elements with the source; closures capturing an object.

**Review question.** For every mutation, name the object and ask who else holds it. For every object handed out of a function or class, ask whether the caller can mutate internal state through it.

# 8. Immutable style: why some code never mutates

Code that always builds new values instead of editing (`{ ...state, count: state.count + 1 }` rather than `state.count++`) is said to use an immutable style. It is common in React, Redux and functional code. Reading it: every line produces a new value; nothing is edited; `const` everywhere is natural. The one check is Bug A: the new value must be stored or returned.

# 9. Decision procedure for any line

1. Is the value a primitive (string, number, boolean)? Then nothing can mutate it; the only check is whether the method's result is stored.
2. Is the value an array, object, Map, Set or Date? Find the method or operation in the tables above: mutates, or returns new?
3. If it mutates: who else holds this object? Parameter, shared, returned, cached? That is the finding.
4. If it returns new: is the result assigned, returned or used? If it is alone on a line, that is the finding.
5. If a copy was intended: is it deep enough for what gets edited next?

**One sentence to keep.** Immutable: every change is a new value, so store it. Mutable: changes happen in place, so know which methods mutate and who else is holding the object.
