(** Strategy-neutral daily portfolio evaluator. Targets are strategy outputs;
    this module does not synthesize signals or tune parameters. *)

type observation = {
  session : string;
  symbol : string;
  sector : string;
  regime : string;
  signal_id : string;
  feature_available_at : Timestamp.t;
  universe_available_at : Timestamp.t;
  adv_available_at : Timestamp.t;
  borrow_available_at : Timestamp.t;
  decision_at : Timestamp.t;
  entry_at : Timestamp.t;
  exit_at : Timestamp.t;
  eligible : bool;
  target_weight_bps : int;
  forward_total_return_1e8 : int64;
  benchmark_return_1e8 : int64;
  sector_return_1e8 : int64;
  adv_money_units : int64;
  one_way_cost_bps : int;
  borrow_available : bool;
  borrow_rate_bps_annual : int;
  borrow_days : int;
  source_id : string;
  source_sha256 : string;
  quality : string;
  data_status : string;
}

type config = {
  strategy_name : string;
  hypothesis_sha256 : string;
  primary_specification_id : string;
  source_name : string;
  source_url : string;
  license : string;
  cost_model_id : string;
  cost_source : string;
  universe : string list;
  initial_equity_money_units : int64;
  max_gross_exposure_bps : int;
  max_abs_net_exposure_bps : int;
  max_abs_name_weight_bps : int;
  max_participation_bps : int;
  variants_attempted : int;
  periods_per_year : int;
}

type day = {
  session : string;
  entry_at : Timestamp.t;
  exit_at : Timestamp.t;
  regime : string;
  gross_return_1e8 : int64;
  net_return_1e8 : int64;
  doubled_cost_return_1e8 : int64;
  benchmark_return_1e8 : int64;
  sector_return_1e8 : int64;
  turnover_bps : int64;
  transaction_cost_1e8 : int64;
  borrow_cost_1e8 : int64;
  starting_equity : int64;
  gross_equity : int64;
  net_equity : int64;
  doubled_cost_equity : int64;
  benchmark_equity : int64;
  sector_equity : int64;
  active_names : int;
}

type position = {
  session : string;
  symbol : string;
  sector : string;
  regime : string;
  eligible : bool;
  target_weight_bps : int;
  forward_total_return_1e8 : int64;
  turnover_bps : int64;
  order_notional_money_units : int64;
  participation_bps : int64;
  one_way_cost_bps : int;
  borrow_cost_1e8 : int64;
  capacity_money_units : int64 option;
  source_id : string;
  source_sha256 : string;
}

type metric = {
  periods : int;
  start_session : string option;
  end_session : string option;
  initial_equity : int64;
  final_equity : int64;
  annualized_return : float option;
  annualized_volatility : float option;
  sharpe : float option;
  max_drawdown_bps : int64;
  annualized_turnover : float option;
  total_turnover_bps : int64;
  mean_period_return_bps : float option;
  worst_period_return_1e8 : int64 option;
  best_period_return_1e8 : int64 option;
}

type output = {
  split_start_session : string;
  all_days : day list;
  positions : position list;
  full_gross : metric;
  full_net : metric;
  full_double : metric;
  in_sample_net : metric;
  out_of_sample_net : metric;
  full_benchmark : metric;
  full_sector_benchmark : metric;
  annual_net : (int * metric) list;
  regime_net : (string * metric) list;
  source_hashes : string list;
  input_rows : int;
}

val validate_config : config -> unit Serror.t
val validate_observation : observation -> unit Serror.t
val run : config -> observation list -> output Serror.t
