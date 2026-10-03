# Contracts for a global exposure system

Implemented API: `core.py` and JSON runner schema in `README.md`. The contracts below are design proposals
for later adapters, not implemented extractors or a migration of another owner's tables.

## Factor observation

`factor_id, canonical_id, representation_id, economic_channel, family, role, unit, currency,
observation_start, observation_end, published_at, available_at, ingested_at, source_vintage,
source_hash, value, missing_reason, revision_of`.

Observation period, first publication and current-vintage availability are distinct. No universal lag can
replace provenance. Representation ids distinguish the same channel measured as level, change, surprise,
return or exposure interaction. Annual point-in-time files do not become monthly information by interpolation.

## Exposure edge

`instrument_id, legal_entity_id, project_id, counterparty_id, factor_id, valid_from, known_at,
direction, magnitude_or_range, units, contract_type, pass_through_terms, termination_terms,
source_document, source_span, evidence_status, confidence_method`.

Status is observed / inferred / hypothesis / unknown. Unknown direction is not zero. Rates, credit and FX
are risk controls even when they are efficiently priced. Alpha hypotheses additionally require a payer,
mechanism, reason information may be underincorporated, instrument and cost/capacity argument.

## Factor relationships

`left, right, relationship, valid_from, known_at, evidence` where relationship is alias,
correlated_proxy, parent_channel, downstream_mediator, interaction, or common_latent_candidate.

Aliases must share a canonical id and cannot enter twice. Correlation does not identify aliasing or causation.
A delay and the resulting lost revenue may be two measurements of one pathway; adding independent P&L shocks
for both would double count the same loss. Alternative taxonomies are views, not additive risk buckets.

## Risk context

`as_of, valuation_currency, holding_horizon, universe, positions, eligible_hedges, position_limits,
liquidity_limits, financing_terms, transaction_costs, valuation_model_version`.

Classify separately: commonness, empirical concentration sensitivity, hedge span, executable hedge coverage,
liquidity/funding constraints, nonlinear/tail exposure and epistemic uncertainty. No factor receives a permanent
"diversifiable" tag independent of this context. Nonlinear scenarios use instrument repricing, not a forced
linear-beta explanation.

## Output to strategy/risk/execution

`as_of, source_versions, exposures, covariance_version, signed_risk_contributions,
overlap_diagnostics, unexplained_risk, hedge_gap, validity_horizon, limitations`.

Strategy chooses intentional exposures; portfolio construction limits unwanted ones; execution consumes the
cached approved limits. Forecasts for different outcomes are not pooled as interchangeable votes. The initial
module returns retrospective attribution and risk estimates only, never buy/sell instructions.
