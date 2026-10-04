# Open work: everything still missing, ordered

Status: operator gap list for the alpha build. Owner: sebas. Date: 2026-10-04, end of the long
session. Companion documents: `docs/plan/alpha-build.md` owns the stages and rules,
`docs/plan/what-is-missing.md` owns the strategy-level gaps, `docs/plan/continuity.md` owns the state
log, `docs/truths.md` owns the claims (T1 to T50).

## 0. What the record now holds

Stages 1, 2, 2b, 3 and 4 are delivered with artifacts and truths. The best measured configuration is
the three-sleeve portfolio at Sharpe 1.549 with a -9.0 percent drawdown inside its window, and T49
says plainly that the window is favorable by construction. The forward window (T50) is declared,
armed and awaiting its first new filing. Nothing in the repository is a fresh-holdout result.

## 1. Claims we cannot make yet, and the experiment each one needs

1. **A stable cross-era edge.** The composite is -13.86 percent in sample against +27.53 out of
   sample (T49). Needed: a rolling-origin evaluation of all three sleeves with refits every quarter,
   reported per era, before any more single-split results are quoted.
2. **The capex sleeve's economics.** Its event-level sign is coherent (T43) and its sleeve is a
   disaster in sample (-49.46 percent, T49). Needed: a regime and group decomposition of the capex
   event effect, and a declared decision between three options: keep it as a hedge only, convert it
   into a gate on the charge signal, or drop it.
3. **The gate's robustness.** The gated expression is +10.48 percent with a -16.3 percent drawdown
   (T44) in one window with one gate rule. Needed: sensitivity to the confirmation threshold, a
   walk-forward refit of the gate model, and an era split.
4. **The council applied to the drivers.** The portfolio combination of the three sleeves is not the
   council. The council's calibration, gating and fusion (T39) has never been run on the driver
   panels at the complex scale. Needed: the same three-block council on the complex panels, with the
   three numbers the design asks for, at breadth inside the complex.
5. **The joint law on real marginals.** The coupling layer has only synthetic contracts. Needed: the
   multi-horizon equity case (return horizons for a filing event) or the risk cache's twelve heads,
   with the measured entanglement from data.
6. **Any capital-scale claim.** Capacity exists per sleeve (median 56.2 and 42.4 million at one
   percent, T47) and for the engine (1.17 million median, 71 thousand at the tenth percentile, T32),
   but the combined portfolio's capacity curve is not computed. Needed: the participation-based
   capacity of the weighted portfolio and a size at which the binding sleeve is the constraint.

## 2. Data gaps, binding one first

1. **The intensity expression's capacity is the binding constraint** at 71 thousand at the tenth
   percentile. Needed: more names in the charge signal's universe, or acceptance of a thin overlay.
2. **Borrow and short availability** are unmeasured on every short leg. Needed: a borrow data source
   or a declared assumption, plus a shortability filter on the bottom bins.
3. **Volume and ADV** exist for the complex names only (59 series). Needed: volume for the driver
   sleeves' names so costs stop being flat twenty basis points.
4. **Options history is paid and the captures are forward only** (three snapshots, twelve names).
   Needed: a scheduled daily capture and a declared implied-move anchor for live sizing; the
   cross-sectional IV test belongs to another session.
5. **The risk cache needs five whole UTC dates.** Today's six-hour BTC block supplies one. Needed:
   four more dated captures and then the plan builder and the declared council comparison.
6. **Intraday equity data does not exist here**, so no execution-quality claim on equities is
   possible. The microstructure work stays on the BTC tape.
7. **New concepts** (backlog, contract assets, capex guidance) are unfetched. Needed: the same
   companyconcept path for a declared concept list, clocks verified per concept.

## 3. Method gaps

1. **No rolling-origin harness.** Every result is one 70/30 split. The forward window is the manual
   substitute.
2. **No variant registry.** The design's rule is to count every tried variant; the repository records
   studies but not a running trial tally, so no multiplicity statement is possible.
3. **No calibration diagnostics.** Reliability, ECE and tail coverage are absent although the
   architecture document requires them.
4. **Intervals are stage-local.** The month-blocked bootstrap exists in two runners; the intensity
   engine's cohort statistics still carry no interval.
5. **Event-level dependence between sleeves is not decomposed.** The daily correlations are
   measured; the shared-name, shared-quarter overlap is not.
6. **Weighting schemes were never compared.** Inverse-volatility beat equal gross on its window; a
   declared comparison against equal risk and hierarchical risk parity is missing.
7. **Cost models differ across sleeves** (flat twenty basis points against volume buckets). One
   model, one owner, is missing.

## 4. Engineering and hygiene

1. **`make check` is red** because another session's untracked draft
   `docs/inbox/regime-factor-program-2026-10-04.md` references five files that do not exist. That
   owner must write them or drop the references; nothing of theirs was touched.
2. **The Makefile holds another session's uncommitted hunk** (eight targets). It has been preserved
   through every commit by staging only my own hunk. Do not discard it.
3. **Superseded byproducts** from the early build, the first revenue and capex driver vintages and
   their universe twins, were unusable because of the 400-day clock. They were deleted at the end of
   the session; the corrected-clock `-pit` files and the `universe-` files are the owners.
4. **Scheduling is installed.** `quanthacks-daily.timer` runs the forward snapshot and the option
   capture at 02:17 UTC daily, `quanthacks-tape.timer` starts one BTC block at 08:02 UTC daily until
   five whole dates exist (`scripts/tape_block_due.py` makes it self-limiting). Units live in
   `scripts/systemd/` and are installed under `~/.config/systemd/user/`. Disable with
   `systemctl --user disable --now quanthacks-tape.timer` once the risk cache has its dates.
5. **Cache hygiene**: the bar cache still holds roughly two hundred tickers with bad data, excluded
   per run by the drivers but not by the intensity engine, whose calendar was diluted once already.
   Needed: one quarantine list consulted by every load path.

2b. **Shared tracked files are being rewritten by another session, and one truth was lost that
   way.** Truth T54 was dropped from `docs/truths.md` by such a rewrite and restored from its artifact.
   The same happened to lines in the Makefile and `results/README.md`. After editing any shared tracked
   file, verify the change is still present before committing, and commit the same minute. Both the Makefile and
   `results/README.md` have had my lines dropped by that session's rewrites, and both had to be
   restored and re-committed. Rule for the next session: after editing a shared tracked file, verify
   the line is still there before committing, and commit the same minute.

## 5. Vision gaps, unchanged from the architecture document

1. **The bundle ladder** is implemented once, not as a routine with entry rules at each level.
2. **Fine-tune rounds with drift monitors and rollback** do not exist.
3. **The policy layer** has sizing and a volatility target but no attribution per specialist, no
   hedging, and no drawdown rule beyond the target.
4. **Quantum** is a tested prototype with a synthetic receipt, not an integrated specialist with an
   equal-budget classical win.
5. **A model registry** is missing; the snapshots' parameter digests are a beginning, not a registry.
6. **Scenario and tail diagnostics** are missing.

## 6. Risks that could invalidate what we quote

1. **Survivorship in the complex register.** The names were chosen with hindsight; the complex effect
   may be selection. Needed: a point-in-time universe rule (SIC and size at each date) and a rerun.
2. **Price-adjustment provenance.** The original 298-series cache predates the adjustment rule; the
   sanity rule now screens it, but the rule's status per series is not recorded.
3. **Overlapping windows and clustered events**, so intervals understate the true uncertainty.
4. **One favorable era.** T49 is the standing warning.
5. **The refresh path proves freshness but not history**: the forward window is the only clean test.

## 7. Priority order

Completed on 2026-10-04, with the truth that owns each: rolling origin and the capex retirement (T51),
combined capacity and its correction (T52), the council on the complex panels (T53), calibration,
tails and the variant registry (T54), the matched-universe test (T55), the gate recalibration, which
failed its falsifier (T56), and the margins and assets candidates (T57). The scheduled captures run
unattended (daily forward snapshot, daily option capture, daily tape block until five dates).

What remains, in order:

1. **Sizing and selection decoupling, measured (T59).** The rule lifted the revenue sleeve to +37.56
   percent at Sharpe 0.942 and the composite to 1.525, but the drawdown worsened to -14.6 percent and the
   composite difference spans zero over ninety months. It is now a declared candidate for the forward
   window rather than a new headline; the raw-conviction sleeve stays primary until the window separates
   them. Assets and margins stay declined, and the pure z-variant stays rejected.
2. **Reconcile the promotion gate with the expectation vintages.** Another session's
   `scripts/report_promotion_gate.py` still reports "expectation vintages missing" while the repository
   holds over eleven thousand measured, clock-verified vintages (T45 to T46). That edit is theirs and
   needs the captain's word; the matching convention is that every specialist in
   `docs/specialists/registry.jsonl` names the manifest node ids it reads, so the two registries cannot
   drift apart.
3. **The fusion family as a sleeve: closed (T60, T61).** Conviction, sign and split sizing all lost to
   the single specialist, and the split rule recovered the net without the quality. No further fusion
   for positions is worth a development run; the council stays in the decision layer and in size
   calibration. The development levers on this line are exhausted.
4. **The risk track**, once the tape has five whole dates: the declared council comparison and the
   coupling layer over its twelve marginals.
5. **The forward window**, running; it closes at 250 scored events or twelve months.
5b-pre0. **Grid load is closed as measured (T63, T64, T66).** Growth, seasonal-level, peak, ramp and
   acceleration forms were all tested for information, pricing and the incremental effect at 582 mapped
   disclosure events; none adds, and the incremental test makes the model worse. The family is retained
   as data, not as a signal.

5b-pre. **First non-SEC results (T63, T64).** The phase overlay was significantly harmful (no phase is
   losing; the sleeve does best in stress), and grid load growth showed no per-name information with an
   unproven cross-section. Neither enters the sleeve yet. The load refinements that the evidence points
   to: load against its own seasonal norm, peak and ramp measures, growth acceleration, and the
   incremental test at disclosure events.

5b. **Non-SEC specialists, the declared next build.** The complex is a power and compute complex, and
   the physical data under it is free and open today: EIA-930 hourly balancing-authority load and
   generation (200 without a key), FRED CSVs (200), FINRA aggregates under the existing credential (200).
   Keyed or blocked for now: PJM, the EIA JSON API, the LBNL queue file, Cloudflare Radar, NOAA CDO.
   The first two specialists are grid load growth by region and the generation mix, and they bring what
   the filings panel cannot: daily or hourly observations, tens of thousands of rows, and a causal link
   to the names the sleeve already trades. Test each with the council's three numbers and the sleeve
   comparison, and let the sequence models run where the sample actually supports depth.
5c. **The judge path is wired (T65).** `make test`, `make reproduce` and `make reproduce-full` cover
   the published numbers with digest comparison; the network tier is opt-in. Any new artifact belongs in
   `results/reproduction-manifest.json` in the same commit that creates it.

6. **The vision gaps** unchanged: the bundle ladder as a routine, fine-tune rounds with drift monitors
   and rollback, the full policy layer, a model registry, quantum only against an equal-budget
   classical win, and scenario and tail diagnostics beyond what T54 covers.

One cheap test from the retirement list is still open: whether a capex surprise works as a **risk
gate** rather than a sleeve. It is optional and low priority given T51.

## 8. Stop conditions

If the forward window fails any of its five declared falsifiers, the composite is finished as a
portfolio and what remains is the gated charge expression alone. If the rolling-origin evaluation
shows every sleeve negative outside the recent era, the honest conclusion is that the development
record is a window effect and the programme's value is the measurement discipline, not an edge.
