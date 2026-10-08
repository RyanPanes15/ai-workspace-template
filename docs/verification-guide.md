# Verification Guide — agent-driven runtime checks

Canonical mechanism for the runtime-evidence gate (`workflows/analyze.md` Step 7,
`workflows/fix.md` Step 4) and the reviewer round (`workflows/fix.md` Step 9.5).
**Read before every self-test run. Update after every run that taught something**
(§7). Keep entries terse: rule → why → one worked example with the item ID.

Last updated: <date> (<item-id>: <one-line lesson>)

---

## 1. Environment / stack

Fill in via setup or by hand (project-specific facts go in `context/environment.md`):
- How to start the local stack (frontend URL/port, API port, DB it points at).
- **There is usually exactly one local stack.** A second frontend on another port may
  fail CORS preflight on every API call and look like a defect in your fix. Take
  turns; never start a duplicate.
- Which DB instance / tenant / account the stack and the testers each use. Record
  it on every observation.
- Test accounts live in `AGENTS.local.md` (gitignored). The developer logs in; the
  agent never types credentials into a browser unless explicitly told to.
- Permission-gated controls: reproduce with an account that *has* the permission —
  a lower-privilege account gives a false "disabled".

## 2. Drivers

### 2.1 Scripted driver — default for fix-verification A/B
Prefer the repo's own browser-automation test harness (Puppeteer, Playwright,
Cypress). One throwaway spec run on both sides of the A/B re-runs identically —
which is what makes the control meaningful — and avoids interactive-tool traps
(stale element refs, coordinate drift, swallowed synthetic clicks, throttled hidden
tabs). Ask before committing a spec. Pass the base URL explicitly (shared `.env`
files often point at a remote box).

Authoring traps that produced false results:
- **Clear an input before typing** — `type()` appends; a corrupted password reads
  as "credentials rejected". Assert the typed length.
- Wait for a button to be **enabled**, not merely visible.
- Synthetic `input/change/blur` events often don't drive framework logic (lookups,
  resolvers); a synthetic pass giving byte-identical before/after results is a
  false PASS. Use real key/mouse input.
- Lists behind a search panel need an explicit search before assertions.

### 2.2 Interactive browser tooling — fallback
Use when the scripted driver is busy or the question is exploratory.
- **Hidden/background tabs don't fire `requestAnimationFrame`, emit no long-task
  events, and throttle timers** → timing measurements there are invalid; DOM/value
  assertions remain fine.
- Screenshot coordinates may be scaled vs CSS pixels and change on every resize;
  recompute from `getBoundingClientRect()` each time. A missed coordinate click
  produces "nothing happened" — an invalid trial.
- `element.click()` fires no `mousedown`/`pointerdown`; handlers bound to those never run.
- Element refs go stale after re-render; re-find before acting.
- Network-inspection tools can report zero requests for an active tab; resource-timing
  buffers cap (e.g. 250 entries) and then report "no calls". Cross-check with server logs.
- Cache-busting fetches can be blocked by the harness.

### 2.2.1 Reading compressed API bodies
If responses are compressed (base64 + zlib), decode captures or HAR exports with
`python modules/payload-decode/decode_response.py <file|--text|x.har> --summary`
before asserting on them. Keep decoded data in `_work/`.

### 2.3 Assert which build is loaded
On every A/B across a code edit, prove each side ran the intended code (a token unique
to each side, fetched from the dev server, or a console marker). Minifiers/bundlers
can strip comments and console calls — pick a marker that survives.

## 3. UI interaction pitfalls (generic)

- **An unmounted control reads as `null`**, indistinguishable from "unchanged".
  After a mode/tab switch, switch back (re-mount) or read form/store state; assert
  the control exists before trusting the read.
- **Auto-dismissing toasts** — capture in the same batch as the triggering click.
- **Component test IDs are often suffixed** by the component (`_CONTAINER`, `_MODAL`,
  `_OK`); an observer on the bare ID reads zero transitions while the dialog is on
  screen. Assert the selector matches something on a known-good case first.
- **The first click after a blur is often swallowed** (re-render under the pointer).
  Verify by an observable effect, never by the click's return value.
- Blur with `Tab`, not by clicking "empty" space (may hit collapse toggles/menus).
- Layout shifts after banners → re-screenshot before coordinate clicks; zoom-verify
  edited fields before every submit.
- Segmented date fields: the test ID may sit on a hidden value input; the editable
  part is a sibling. Focus the section, type, Tab, verify the value.
- A page reload re-initialises module state and skips in-app navigation code — use a
  real in-app round-trip when the bug involves navigation.

## 4. Test design

- **Pre-fix control first** — it must reproduce the reported symptom on the same
  record, instance, and input path.
- **Name the discriminating check** — some checks pass even before the fix.
- **Negative control** — a variation that should not reproduce; also proves the
  machinery under test is live.
- Representative data volume (server row caps, pagination thresholds).
- A concurrency race may not reproduce on a slow local stack; say so.

## 5. Measurement recipes

### 5.1 Render latency
Instrument with a MutationObserver / performance marks around the interaction; one
non-interleaved run is not a measurement — alternate A/B runs, several each. Two
probes of the same class agreeing is not corroboration (both may be throttled).

### 5.2 Input-path coverage — one value, several commit paths
**A negative result is valid only for the input path you drove.** Read the handler
binding (`onBlur` / `onChange` / `onClose`) in the markup first, then drive every
path that can commit the value:

| Path | Typically fires |
| --- | --- |
| Typing | change per keystroke/section, blur on focus loss |
| Picker / popup | change via programmatic set, then close — the input may blur when the popup **opens** (old value) |
| Paste | change only |
| Keyboard stepper | change; blur only on focus loss |
| Clear button | change with empty value, no focus |
| Programmatic seed / sibling auto-fill / dialog return | programmatic set only |
| IME / full-width conversion | composition events, then change |

**Corollary — the field's state must arm the code path.** Guards like `isValid(value)`,
`if (!value) return`, dirty flags, row selection, or frozen grids silently disarm a
test. Name the guard and satisfy it (e.g. commit a value first, then reopen a picker).

### 5.3 Probing live state without changing it
A probe is evidence only if it leaves the state intact. Dynamic `import()` of a module
in the console can load a **duplicate instance** (empty store) or tear down rendered
UI; post-hot-reload probes can read a dead module. Prefer real UI actions; when you
must reach in, open with a liveness assertion against a known on-screen value and read
raw output (no `tail` truncation). Temporary console instrumentation in the component
is often the cleanest probe — revert it after.

## 6. Known test records

Keep project-specific records in `context/test-records.md`: record keys, which
instance/tenant, what state it is in, date verified. Re-verify state before reuse.

## 7. Maintenance rule

When asked to run a screen test: (1) read this file; (2) run; (3) append any new
pitfall, recipe, or environment fact — generalized rule + item ID; (4) bump
"Last updated".
