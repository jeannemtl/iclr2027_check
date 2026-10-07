---
title: "Reading a TypeScript Declaration"
subtitle: "Every variation of `const o: { a?: number } = {}` — the three slots and what can go in each"
date: "October 2026"
---

**The shape**

Every declaration has three slots. Only the first and last are required; the middle one (the type) is TypeScript's addition and runs nothing.

```ts
const  o  :  { a?: number }  =  {} ;
^^^^^  ^     ^^^^^^^^^^^^^^     ^^
1      2     3                  4
```

1. **keyword**: `const` (cannot rebind), `let` (can rebind), `var` (old, avoid).
2. **name**: the label.
3. **`: TYPE`**: what the compiler will allow in this label. Erased at runtime. Optional; omitted, TS infers it from the value.
4. **`= VALUE`**: the runtime value. Optional with `let` (then the value is `undefined`).

Python parallel: `o: dict = {}` has the same three slots; Python ignores the hint, TS enforces it.

**Slot 1: the keyword**

<table>
<thead><tr><th>Form</th><th>Meaning</th><th>Python</th></tr></thead>
<tbody>
<tr><td><code>const x = 1</code></td><td>label fixed; contents of an object/array still mutable</td><td>no equivalent (convention: never rebind)</td></tr>
<tr><td><code>let x = 1</code></td><td>label can be reassigned later</td><td>ordinary <code>x = 1</code></td></tr>
<tr><td><code>let x;</code></td><td>declared, value <code>undefined</code>, type <code>any</code> unless annotated</td><td><code>x = None</code></td></tr>
<tr><td><code>let x: number;</code></td><td>declared with a type, no value yet; TS errors if read before assignment</td><td></td></tr>
<tr><td><code>var x = 1</code></td><td>function-scoped, hoisted; smell in modern code</td><td></td></tr>
</tbody>
</table>

**Slot 3: the type, every form you will meet**

<table>
<thead><tr><th>Written</th><th>Reads as</th><th>Example value</th></tr></thead>
<tbody>
<tr><td><code>: number</code></td><td>a number</td><td><code>1</code>, <code>2.5</code>, <code>NaN</code></td></tr>
<tr><td><code>: string</code></td><td>a string</td><td><code>&quot;a&quot;</code></td></tr>
<tr><td><code>: boolean</code></td><td><code>true</code> or <code>false</code></td><td><code>true</code></td></tr>
<tr><td><code>: null</code> / <code>: undefined</code></td><td>exactly that value</td><td></td></tr>
<tr><td><code>: any</code></td><td>anything, checking off</td><td>✗ in review</td></tr>
<tr><td><code>: unknown</code></td><td>anything, must narrow before use</td><td>✓ for external data</td></tr>
<tr><td><code>: void</code></td><td>returns nothing useful (functions)</td><td></td></tr>
<tr><td><code>: never</code></td><td>never returns (throws, loops forever)</td><td></td></tr>
<tr><td><code>: number[]</code></td><td>array of numbers</td><td><code>[1, 2]</code></td></tr>
<tr><td><code>: Array&lt;number&gt;</code></td><td>same as <code>number[]</code></td><td><code>[1, 2]</code></td></tr>
<tr><td><code>: string[][]</code></td><td>array of arrays of strings</td><td><code>[[&quot;a&quot;], [&quot;b&quot;, &quot;c&quot;]]</code></td></tr>
<tr><td><code>: [string, number]</code></td><td>tuple: exactly a string then a number</td><td><code>[&quot;a&quot;, 1]</code></td></tr>
<tr><td><code>: { a: number }</code></td><td>object with REQUIRED key <code>a</code></td><td><code>{ a: 1 }</code></td></tr>
<tr><td><code>: { a?: number }</code></td><td>object with OPTIONAL key <code>a</code> (<code>number | undefined</code>)</td><td><code>{}</code> or <code>{ a: 1 }</code></td></tr>
<tr><td><code>: { a: number; b?: string }</code></td><td>two keys; <code>;</code> or <code>,</code> separates them</td><td><code>{ a: 1 }</code></td></tr>
<tr><td><code>: { readonly a: number }</code></td><td>key cannot be reassigned (compile-time only)</td><td></td></tr>
<tr><td><code>: { [key: string]: number }</code></td><td>any string key, number values (index signature)</td><td><code>{ x: 1, y: 2 }</code></td></tr>
<tr><td><code>: Record&lt;string, number&gt;</code></td><td>same as the index signature above</td><td><code>{ x: 1 }</code></td></tr>
<tr><td><code>: Map&lt;string, number&gt;</code></td><td>a Map from strings to numbers</td><td><code>new Map()</code></td></tr>
<tr><td><code>: Set&lt;string&gt;</code></td><td>a Set of strings</td><td><code>new Set()</code></td></tr>
<tr><td><code>: string | number</code></td><td>union: either</td><td><code>&quot;a&quot;</code> or <code>1</code></td></tr>
<tr><td><code>: string | null</code></td><td>a string or null</td><td><code>null</code></td></tr>
<tr><td><code>: &quot;a&quot; | &quot;b&quot;</code></td><td>literal union: only those two strings</td><td><code>&quot;a&quot;</code></td></tr>
<tr><td><code>: A &amp; B</code></td><td>intersection: has everything in A and B</td><td></td></tr>
<tr><td><code>: User</code></td><td>a named interface/type declared elsewhere</td><td></td></tr>
<tr><td><code>: User[]</code></td><td>array of that named type</td><td></td></tr>
<tr><td><code>: Partial&lt;User&gt;</code></td><td><code>User</code> with every key optional</td><td><code>{}</code></td></tr>
<tr><td><code>: Required&lt;User&gt;</code></td><td><code>User</code> with every key required</td><td></td></tr>
<tr><td><code>: Pick&lt;User, &quot;id&quot;&gt;</code></td><td>only the <code>id</code> key of <code>User</code></td><td></td></tr>
<tr><td><code>: Omit&lt;User, &quot;id&quot;&gt;</code></td><td><code>User</code> without <code>id</code></td><td></td></tr>
<tr><td><code>: Promise&lt;User&gt;</code></td><td>a promise that resolves to a <code>User</code></td><td><code>fetchUser()</code></td></tr>
<tr><td><code>: () =&gt; void</code></td><td>a function taking nothing, returning nothing</td><td><code>() =&gt; {}</code></td></tr>
<tr><td><code>: (x: number) =&gt; string</code></td><td>a function from number to string</td><td><code>(x) =&gt; String(x)</code></td></tr>
<tr><td><code>: (...args: unknown[]) =&gt; void</code></td><td>a function taking any arguments</td><td></td></tr>
<tr><td><code>: typeof DEFAULTS</code></td><td>the type of an existing value</td><td></td></tr>
<tr><td><code>: keyof User</code></td><td>union of <code>User</code>&#x27;s key names</td><td><code>&quot;id&quot; | &quot;name&quot;</code></td></tr>
</tbody>
</table>

**Slot 4: the value**

<table>
<thead><tr><th>Written</th><th>Reads as</th></tr></thead>
<tbody>
<tr><td><code>= {}</code></td><td>empty object</td></tr>
<tr><td><code>= { a: 1 }</code></td><td>object with key <code>a</code></td></tr>
<tr><td><code>= { a }</code></td><td>shorthand for <code>{ a: a }</code> (key and variable share a name)</td></tr>
<tr><td><code>= { ...o, b: 2 }</code></td><td>copy of <code>o</code> with <code>b</code> added or overridden</td></tr>
<tr><td><code>= []</code></td><td>empty array</td></tr>
<tr><td><code>= [1, 2]</code></td><td>array literal</td></tr>
<tr><td><code>= [...a, ...b]</code></td><td>concatenation</td></tr>
<tr><td><code>= new Map()</code> / <code>= new Set()</code></td><td>empty Map / Set</td></tr>
<tr><td><code>= new Map([[&quot;k&quot;, 1]])</code></td><td>Map seeded from pairs</td></tr>
<tr><td><code>= (x) =&gt; x * 2</code></td><td>arrow function</td></tr>
<tr><td><code>= async () =&gt; { ... }</code></td><td>async arrow, returns a Promise</td></tr>
<tr><td><code>= await f()</code></td><td>the unwrapped result of a Promise (inside <code>async</code>)</td></tr>
<tr><td><code>= f()</code></td><td>whatever <code>f</code> returns; if <code>f</code> is async this is a Promise ✗</td></tr>
<tr><td><code>= cond ? a : b</code></td><td>ternary</td></tr>
<tr><td><code>= x ?? 10</code></td><td><code>x</code>, or 10 if <code>x</code> is null/undefined</td></tr>
<tr><td><code>= x || 10</code></td><td><code>x</code>, or 10 if <code>x</code> is falsy</td></tr>
<tr><td><code>= x as User</code></td><td>cast; no runtime check</td></tr>
<tr><td><code>= x!</code></td><td>assert non-null; no runtime check</td></tr>
<tr><td><code>= value as const</code></td><td>freeze literals into literal types</td></tr>
<tr><td><code>= value satisfies User</code></td><td>check against <code>User</code> without widening</td></tr>
</tbody>
</table>

**Mixed: destructuring in slot 2**

<table>
<thead><tr><th>Written</th><th>Reads as</th><th>Python</th></tr></thead>
<tbody>
<tr><td><code>const { a, b } = o</code></td><td>pull <code>o.a</code> and <code>o.b</code> into <code>a</code> and <code>b</code></td><td><code>a, b = o[&quot;a&quot;], o[&quot;b&quot;]</code></td></tr>
<tr><td><code>const { a: x } = o</code></td><td>pull <code>o.a</code> into a variable named <code>x</code></td><td></td></tr>
<tr><td><code>const { a = 5 } = o</code></td><td>pull <code>o.a</code>, default 5 if undefined</td><td><code>o.get(&quot;a&quot;, 5)</code></td></tr>
<tr><td><code>const { a, ...rest } = o</code></td><td><code>a</code>, and <code>rest</code> = the other keys</td><td></td></tr>
<tr><td><code>const [x, y] = arr</code></td><td>first two elements</td><td><code>x, y = arr[:2]</code></td></tr>
<tr><td><code>const [x, , z] = arr</code></td><td>skip the second</td><td></td></tr>
<tr><td><code>const [head, ...tail] = arr</code></td><td>first and the rest</td><td><code>head, *tail = arr</code></td></tr>
<tr><td><code>const { a }: { a: number } = o</code></td><td>destructure with a type annotation</td><td></td></tr>
<tr><td><code>for (const [k, v] of Object.entries(o))</code></td><td>destructure each pair in a loop</td><td><code>for k, v in o.items()</code></td></tr>
</tbody>
</table>

**Same slots in a function signature**

```ts
function f(id: string, n: number = 0, opts?: Options): Promise<User> { ... }
           ^^^^^^^^^^  ^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^   ^^^^^^^^^^^^^
           required    default value   optional         return type
```

<table>
<thead><tr><th>Written</th><th>Reads as</th></tr></thead>
<tbody>
<tr><td><code>id: string</code></td><td>required parameter of type string</td></tr>
<tr><td><code>n: number = 0</code></td><td>parameter with default; type inferred if omitted (<code>n = 0</code>)</td></tr>
<tr><td><code>opts?: Options</code></td><td>optional parameter; inside, <code>opts</code> is <code>Options | undefined</code></td></tr>
<tr><td><code>...rest: number[]</code></td><td>collect remaining arguments</td></tr>
<tr><td><code>): Promise&lt;User&gt;</code></td><td>return type; <code>async</code> functions always return a Promise</td></tr>
<tr><td><code>): void</code></td><td>returns nothing</td></tr>
<tr><td><code>): x is Circle</code></td><td>type guard: returns boolean, narrows <code>x</code></td></tr>
<tr><td><code>&lt;T&gt;(x: T): T</code></td><td>generic: whatever type goes in comes out</td></tr>
<tr><td><code>const f = (x: number): string =&gt; ...</code></td><td>arrow with param and return types</td></tr>
</tbody>
</table>

**Same slots in a class**

```ts
class A {
  private x = 1;                       // field with inferred type number
  readonly id: string;                 // field declared, assigned in constructor
  static count = 0;                    // on the class, not instances
  constructor(public name: string) {}  // parameter property: declares AND assigns this.name
  get total(): number { return 0 }     // getter, read as a.total
}
```

**Decoding checklist**

1. Find the `=`; everything left is the declaration, everything right is the runtime value.
2. On the left, find the `:`; everything after it up to `=` is the type and runs nothing.
3. In the type, `?` after a key means optional, `|` means or, `[]` after a type means array of, `<>` means generic parameter.
4. In the value, `{}` is an object, `[]` is an array, `=>` is a function, `new` builds an instance, `await` unwraps a Promise.
5. Ask: can the value at runtime actually be what the type says? `as`, `!`, `any`, and `JSON.parse` are the places the answer can be no.
