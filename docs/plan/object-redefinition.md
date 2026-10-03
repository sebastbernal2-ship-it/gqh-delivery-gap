# Object redefinition: three outcomes on the same panel

Declared before fitting, on 2026-10-03.

## Why

Truth T2 says the median revision is noise, 36 percent of first revisions are one month or less, and the
information sits in the tail. Every model so far used the first revision of any size as the outcome, which means
the object was mostly noise by our own measurement. The panel and the factors already exist, so redefining the
outcome costs one afternoon and has never been tried.

## The three outcomes, all computed from the same promise series

| Outcome | Definition |
|---|---|
| `event` | the first month the promise changed, any size. The baseline, already measured. |
| `event_large` | the first month the promise changed by **six months or more**. The tail. |
| `event_withdraw` | the first available vintage month in which the generator is absent from the planned sheet while its promise was still in the future, and absent again in the next available vintage. Suspected withdrawal. |

`event_withdraw` carries a stated ambiguity: a unit that begins operating early also leaves the planned sheet. The
share of withdrawals that could be early completions is measured and reported alongside, because we tracked 64
percent of generators as late, which bounds how often early completion can explain an exit.

## Declared expectations, written before any fit

- **`event_large`**: the factor set should discriminate **better** than on `event`, because the outcome is no
  longer dominated by one month nudges. Construction spending and delivery times should point **positive**:
  more building and longer waits mean larger slips.
- **`event`**: expected to stay where it is, at or below the controls only baseline, since this was the object
  that already failed.
- **`event_withdraw`**: exploratory, no sign declared except pipeline momentum, where more planned capacity in a
  state is expected to **raise** the chance of withdrawal, because a crowding queue raises the cost of staying.

## Nulls and multiplicity

Two nulls for every fit, both reported: the controls only model, and the block shuffle placebo that permutes the
factor block across projects within each month. Primary comparisons = three outcomes x two nulls = six. All six
are reported. No outcome is dropped for being uninteresting, and no selection happens after the fact.

## The decision this changes

If `event_large` does not beat controls only in the test window, then the object was not the problem, and the
drivers of schedule risk are not in public aggregates at this resolution. That closes the delivery direction on
this data, and the remaining work on it becomes the queue history request.

---

# Results, run 2026-10-03

Panel `results/delivery-panel-objects.csv`: 27,708 project months, 2,190 first revision months, 576 large
revisions of six months or more, 639 suspected withdrawals. Training through 2019, testing from 2020. Both
inside the mechanism study development window, which ends 2022-09.

| Outcome | Events | Controls only, test AUC | Controls plus factors | Placebo |
|---|---|---|---|---|
| `event`, any size | 2,190 | 0.6213 | 0.5697 | 0.5559 |
| `event_large`, six months or more | 576 | **0.6345** | 0.6407 | **0.6437** |
| `event_withdraw`, suspected exit | 639 | **0.6624** | 0.5659 | 0.5639 |

**Two things happened, and they point in opposite directions.**

The object was part of the problem. The controls, which are technology, size, age and start year, discriminate
the tail at 0.6345 and exits at 0.6624 against only 0.6213 for the nudge dominated first revision. So the
redefinition worked: the tail and the exits are substantially more structured than the object everyone models,
which is exactly what truth T2 predicted.

The factors are still the problem. On the tail the factor model edges past controls at 0.6407, and the
**placebo reaches 0.6437**, so the gain is the seven extra parameters and not the information in them. On exits
the factor model collapses out of sample, 0.5659 against controls at 0.6624, with the test likelihood degrading
from minus 994 to minus 8,138. On nudges it loses as before.

Coefficients worth naming on the tail: equipment construction spending 1.374 [1.213, 1.600], the declared
positive sign, and data centre construction spending 0.620 [0.519, 0.723], the declared positive sign reversed.
The largest single coefficient is again the missingness flag for pipeline momentum, 0.532 [0.440, 0.614], which
covers only 44 percent of rows, so coverage and not a factor is doing much of the work.

Specificity on the tail is in the declared direction and small: supply chain pressure reads 1.110 [0.990, 1.332]
in equipment heavy technologies against 0.792 [0.737, 0.895] in the light ones. The heavy estimate includes one,
so this is a hint, not a finding.

**Verdict.** The pre-registered falsification fired. The object was not the whole problem and the factors are
not the answer. Together with the three earlier factor sets this closes the delivery direction on public
aggregates: the structure in the tail is project intrinsic, carried by technology, size, age and vintage, and
the drivers that would move it in a forecast are the host, the contract and the queue, none of which is in this
data. The queue request is the only remaining move on this direction.
