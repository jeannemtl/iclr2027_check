---
title: "One Function, Three Spellings"
subtitle: "Where the types sit, how each line is read, and why one of them will not compile"
date: "October 2026"
---

**The function**

All three lines below define the same thing: an async function that takes a number `x` and resolves to `x * 2`. Its type, in every case, is *a function from a number to a promise of a number*, written `(x: number) => Promise<number>`.

```ts
// Form 1: types on the function, variable inferred
const f = async (x: number): Promise<number> => { return x * 2 };

// Form 2: types on the variable, function bare
const f: (x: number) => Promise<number> = async (x) => { return x * 2 };

// Form 3: function declaration (no variable at all)
async function f(x: number): Promise<number> { return x * 2 }
```

**Vocabulary used below**

| Word | Means | In these examples |
| --- | --- | --- |
| the arrow / the arrow function | a function written with `=>` | `async (x) => { ... }` |
| the async function | a function marked `async`; always returns a Promise | the same thing, named by its keyword |
| the value / the right-hand side | what comes after `=` | the same thing, named by its position |
| the variable | the name being declared | `f` |
| the variable's type | what comes between `:` and `=` on the left | `(x: number) => Promise<number>` |
| `Promise<number>` | a placeholder that will later hold a number | the return type of any async function returning a number |

# Form 1: types on the function

```ts
const f = async (x: number): Promise<number> => { return x * 2 };
      ^   ^^^^^  ^^^^^^^^^^  ^^^^^^^^^^^^^^^^  ^^  ^^^^^^^^^^^^^^^^^
      2   async  parameter   return type       =>  body
          keyword with type
```

**Token by token**

| Piece | Say | Slot |
| --- | --- | --- |
| `const f` | "constant `f`" | 1, 2 |
| `=` | "is set to" | border |
| `async` | "an async function" | 4 |
| `(x: number)` | "taking a number `x`" | 4 |
| `: Promise<number>` | "that returns a promise of a number" | 4 |
| `=>` | "whose body is" | 4 |
| `{ return x * 2 }` | "return `x` times 2" | 4 |

**Read aloud, whole:** *"Constant `f` is set to an async function taking a number `x`, returning a promise of a number, whose body returns `x` times 2."*

**Where the types are:** both inside the function. The `:` after `x` types the parameter. The `:` after `)` types the return. The variable `f` has no annotation (no `:` between `f` and `=`); TypeScript infers `f`'s type from the arrow: `(x: number) => Promise<number>`.

**What is optional here:** the `: Promise<number>`. Drop it and TS still infers `Promise<number>` because the function is `async` and returns a number. The `x: number` is not optional in strict mode: with nothing on the left to supply it, a bare `(x)` would be an implicit `any`.

# Form 2: types on the variable

```ts
const f: (x: number) => Promise<number> = async (x) => { return x * 2 };
      ^  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  ^ ^^^^^^^^^^  ^^  ^^^^^^^^^^^^^^^^^
      2  3: the TYPE of f                = 4: the VALUE   =>  body
         (a function type)                  async arrow, bare x
```

**Token by token**

| Piece | Say | Slot |
| --- | --- | --- |
| `const f` | "constant `f`" | 1, 2 |
| `: (x: number) => Promise<number>` | "of type: function from a number `x` to a promise of a number" | 3 |
| `=` | "is set to" | border |
| `async` | "an async function" | 4 |
| `(x)` | "taking `x`" (its type comes from the left) | 4 |
| `=>` | "whose body is" | 4 |
| `{ return x * 2 }` | "return `x` times 2" | 4 |

**Read aloud, whole:** *"Constant `f`, of type function-from-number-to-promise-of-number, is set to an async function taking `x` whose body returns `x` times 2."*

**Where the types are:** everything between `:` and `=` is the type of `f`. The arrow on the right has no annotations at all. `x` is still a `number`, because TS reads the expected type on the left and pushes it into the bare parameter. This is called **contextual typing**, and it is the same mechanism that types `x` in `arr.map((x) => x * 2)`: the expected callback type comes from `map`.

**Two arrows, two jobs**

```ts
const f: (x: number) => Promise<number> = async (x) => { return x * 2 };
//                    ^^ "to"                       ^^ "whose body is"
//       └── TYPE (after the colon) ────┘ └── VALUE (after the equals) ──┘
```

| Arrow | Side of `=` | Job | Say |
| --- | --- | --- | --- |
| `(x: number) => Promise<number>` | left, after `:` | describes a shape; runs nothing | "number **to** promise of number" |
| `async (x) => { ... }` | right, after `=` | a real function | "taking `x`, **whose body is** ..." |

The `=` is the border. Left of it is what `f` IS; right of it is what `f` HOLDS.

# Form 3: function declaration

```ts
async function f(x: number): Promise<number> { return x * 2 }
^^^^^ ^^^^^^^^ ^ ^^^^^^^^^^  ^^^^^^^^^^^^^^^^ ^^^^^^^^^^^^^^^^^
async keyword  name param    return type      body
```

**Read aloud:** *"Async function `f`, taking a number `x`, returning a promise of a number, whose body returns `x` times 2."*

No `const`, no `=`, no arrow. The name `f` is part of the function syntax. The types sit in the same two places as Form 1 (after `x`, after `)`). This is the most common form for a standalone, named function in the code you will review.

# The broken one

```ts
const f: (x: number) => async (x) => { return x * 2 };     // ✗ does not compile
```

**Why:** there is no `=`. After the `:` TypeScript is reading a **type** and keeps reading until it finds `=`. It sees `(x: number) =>`, the start of a function type, and now expects a *return type*. It gets `async (x) => {...}`, which is a value, not a type, so it stops with a syntax error. Slot 3 never ended; slot 4 never started.

```ts
const f: (x: number) => async (x) => { return x * 2 };
      2  3 ........................................ ?      no border, so no slot 4
```

**The fix** is to insert the border and finish the type:

```ts
const f: (x: number) => Promise<number> = async (x) => { return x * 2 };
//                      ^^^^^^^^^^^^^^^ ^
//                      finish the type  the border
```

# Side by side

| | Form 1 | Form 2 | Form 3 |
| --- | --- | --- | --- |
| Written | `const f = async (x: number): Promise<number> => {...}` | `const f: (x: number) => Promise<number> = async (x) => {...}` | `async function f(x: number): Promise<number> {...}` |
| Where `x: number` sits | on the arrow | on `f`'s type | on the declaration |
| Where `Promise<number>` sits | after the arrow's `)` | on `f`'s type, after `=>` | after the declaration's `)` |
| Arrow parameters | typed | bare (contextually typed) | n/a |
| Has a `=` | yes | yes | no |
| Number of `=>` | one (value) | two (one type, one value) | none |
| Type of `f` | inferred from the arrow | declared; the arrow must match it | from the declaration |
| `this` inside | the surrounding `this` | the surrounding `this` | depends on how it is called |
| Hoisted (usable before the line) | no | no | yes |
| Meaning | identical | identical | identical |

# Reading rules

1. **Find the `=`.** Left of it (after `:`) is the type and runs nothing. Right of it is the value. No `=`: either a `function` declaration (Form 3) or a callback passed as an argument, or a syntax error.
2. **Two `=>` on one line** means one is in the type and one is in the value; the `=` is between them. Say "to" for the type arrow and "whose body is" for the value arrow.
3. **A bare `(x)` is not `any`.** Ask where its type comes from: the variable's annotation on the left (Form 2), or the method it is passed to (`map`, `then`, `app.get`). Only a bare parameter with nothing on either side is an implicit `any`.
4. **A missing `: Promise<number>` is not a bug.** It is inferred. To work it out yourself: find every `return`; if the function is `async`, wrap the result in `Promise<...>`.
5. **`async` means the return type always starts with `Promise<`**, whether written or inferred. Every caller must `await` it; a caller that uses the result directly is holding the promise, not the value.

# Where each form shows up in real code

| You will see | Form | Note |
| --- | --- | --- |
| `export async function getUser(id: string): Promise<User>` | 3 | most exported functions |
| `const handler = async (req: Request, res: Response) => {...}` | 1 | handlers assigned to a const |
| `const handler: RequestHandler = async (req, res) => {...}` | 2 | when a named function type exists; `req`, `res` typed by `RequestHandler` |
| `app.get("/", async (req, res) => {...})` | callback | no variable; types come from `app.get` |
| `ids.map(async (id) => fetchUser(id))` | callback | gives `Promise<User>[]`; needs `Promise.all` |
| `const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))` | 1 | not async, but returns a Promise explicitly |
