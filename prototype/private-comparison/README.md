# Private comparison UI prototype

> PROTOTYPE — throwaway UI for GitHub issue #8. Do not promote this code directly to production.

Three structurally different Danish catalogue and comparison experiences, switchable with
`?variant=A`, `?variant=B`, or `?variant=C` on the same route:

- **A — Roligt overblik:** catalogue-first cards with a persistent filter rail.
- **B — Kontroltabel:** dense, scan-friendly table with compact controls.
- **C — Beslutningsnotat:** difference-first reading flow centred on obligations and evidence.

The mock offers are illustrative and intentionally include missing or unclear facts. They are
not current commercial offers.

## Run

```sh
python3 prototype/private-comparison/serve.py
```

Then open <http://127.0.0.1:4173/prototype/private-comparison/?variant=A>.

All state is in memory. Use the floating arrows or the keyboard left/right arrow keys to switch
variants. The prototype switcher is only rendered on localhost (or when `?prototype=1` is set).
