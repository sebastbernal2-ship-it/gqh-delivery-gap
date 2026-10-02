(** Exact fixed-point units for the execution kernel.

    Unit policy is owned by {!docs/adr/ADR-007-execution-units.md}.

    - price: 1e-4 ticks, matching {!Price.t} and ADR-004
    - quantity: 1e-6 units
    - money: 1e-8 units
    - rate: 1e-8 fraction units

    All arithmetic is integer and fails closed on overflow. Decimal strings
    are accepted only at the ingestion boundary, where {!parse} converts them
    to units. {!Binance_units} owns venue step and lot alignment; this module
    owns the fixed engine scales. *)

let price_scale = 10_000L
let quantity_scale = 1_000_000L
let money_scale = 100_000_000L
let rate_scale = 100_000_000L

(* notional = price_ticks * quantity_units / notional_divisor *)
let notional_divisor =
  Int64.div (Int64.mul price_scale quantity_scale) money_scale

(* fee = money * bps / 10_000 *)
let bps_divisor = 10_000L

(** ADR-004 caps prices at 32-bit ticks, 214,748.3647. *)
let price_ticks_max = 2_147_483_647L

let ( let* ) result f = Result.bind result f

let decimals_of_scale scale =
  let rec loop decimals remaining =
    if remaining = 1L then Ok decimals
    else if remaining <= 0L || Int64.rem remaining 10L <> 0L then
      Serror.fail "invalid fixed-point scale"
    else loop (decimals + 1) (Int64.div remaining 10L)
  in
  loop 0 scale

let decimals_of_scale_exn scale =
  match decimals_of_scale scale with
  | Ok decimals -> decimals
  | Error message -> invalid_arg message

let checked_mul left right =
  if left = 0L || right = 0L then Ok 0L
  else if left > 0L && right > 0L then
    if left > Int64.div Int64.max_int right then Serror.fail "integer overflow"
    else Ok (Int64.mul left right)
  else if left < 0L && right < 0L then
    if left < Int64.div Int64.max_int right then Serror.fail "integer overflow"
    else Ok (Int64.mul left right)
  else if left < 0L then
    if left < Int64.div Int64.min_int right then Serror.fail "integer overflow"
    else Ok (Int64.mul left right)
  else if right < Int64.div Int64.min_int left then
    Serror.fail "integer overflow"
  else Ok (Int64.mul left right)

let checked_add left right =
  if right > 0L && left > Int64.sub Int64.max_int right then
    Serror.fail "integer overflow"
  else if right < 0L && left < Int64.sub Int64.min_int right then
    Serror.fail "integer overflow"
  else Ok (Int64.add left right)

let digits value =
  if value = "" then Serror.fail "empty decimal digits"
  else
    let rec loop index total =
      if index = String.length value then Ok total
      else
        let char = value.[index] in
        if char < '0' || char > '9' then Serror.fail "invalid decimal digits"
        else
          let* total = checked_mul total 10L in
          let* total =
            checked_add total (Int64.of_int (Char.code char - Char.code '0'))
          in
          loop (index + 1) total
    in
    loop 0 0L

let trim_trailing_zeros value =
  let rec last_nonzero index =
    if index < 0 then -1
    else if value.[index] <> '0' then index
    else last_nonzero (index - 1)
  in
  let last = last_nonzero (String.length value - 1) in
  if last < 0 then "" else String.sub value 0 (last + 1)

let parse ~scale value =
  let decimals = decimals_of_scale_exn scale in
  let negative, value =
    if String.length value > 0 && value.[0] = '-' then
      (true, String.sub value 1 (String.length value - 1))
    else (false, value)
  in
  match String.index_opt value '.' with
  | None ->
      let* whole = digits value in
      let* units = checked_mul whole scale in
      Ok (if negative then Int64.neg units else units)
  | Some point ->
      if String.index_from_opt value (point + 1) '.' <> None then
        Serror.fail "decimal has multiple points"
      else
        let whole = String.sub value 0 point in
        let fraction =
          String.sub value (point + 1) (String.length value - point - 1)
        in
        if whole = "" || fraction = "" then
          Serror.fail "decimal must have digits on both sides of the point"
        else if String.length fraction > decimals then
          let extra =
            String.sub fraction decimals (String.length fraction - decimals)
          in
          if trim_trailing_zeros extra <> "" then
            Serror.failf "decimal %s exceeds the scale precision" value
          else
            let fraction = String.sub fraction 0 decimals in
            let* whole = digits whole in
            let* whole = checked_mul whole scale in
            let* fraction = digits fraction in
            let* units = checked_add whole fraction in
            Ok (if negative then Int64.neg units else units)
        else
          let fraction = fraction ^ String.make (decimals - String.length fraction) '0' in
          let* whole = digits whole in
          let* whole = checked_mul whole scale in
          let* fraction = digits fraction in
          let* units = checked_add whole fraction in
          Ok (if negative then Int64.neg units else units)

let format ~scale value =
  if value = Int64.min_int then invalid_arg "value is out of range"
  else
    let decimals = decimals_of_scale_exn scale in
    let format_positive value =
      let whole = Int64.to_string (Int64.div value scale) in
      let fraction = Int64.rem value scale in
      let digits = Int64.to_string fraction in
      let digits = String.make (decimals - String.length digits) '0' ^ digits in
      let digits = trim_trailing_zeros digits in
      if digits = "" then whole else whole ^ "." ^ digits
    in
    if value < 0L then "-" ^ format_positive (Int64.neg value)
    else format_positive value

let parse_price = parse ~scale:price_scale
let parse_quantity = parse ~scale:quantity_scale
let parse_money = parse ~scale:money_scale
let parse_rate = parse ~scale:rate_scale
let format_price = format ~scale:price_scale
let format_quantity = format ~scale:quantity_scale
let format_money = format ~scale:money_scale
let format_rate = format ~scale:rate_scale

let ticks_of_price (price : Price.t) = Int64.of_int (Price.to_int price)

let price_of_ticks ticks =
  if ticks < 0L then Serror.fail "price ticks must be nonnegative"
  else if ticks > price_ticks_max then
    Serror.failf "price ticks %Ld exceed the ADR-004 range" ticks
  else Ok (Price.of_int (Int64.to_int ticks))

(** [mul_div ~divisor a b] is [a * b / divisor], rounded half away from zero.

    The divisor must be positive and even. The product is never formed
    directly: it is decomposed so the intermediate values stay in int64 while
    the result stays exact for the declared rounding rule. *)
let mul_div ~divisor a b =
  if divisor <= 0L then Serror.fail "divisor must be positive"
  else if a = Int64.min_int || b = Int64.min_int then
    Serror.fail "integer overflow"
  else
    let negative = (a < 0L) <> (b < 0L) in
    let a = if a < 0L then Int64.neg a else a in
    let b = if b < 0L then Int64.neg b else b in
    let whole = Int64.div b divisor in
    let remainder = Int64.rem b divisor in
    let* high = checked_mul a whole in
    let* low = checked_mul a remainder in
    let* low = checked_add low (Int64.div divisor 2L) in
    let low = Int64.div low divisor in
    let* magnitude = checked_add high low in
    if magnitude < 0L then Serror.fail "integer overflow"
    else Ok (if negative then Int64.neg magnitude else magnitude)

(** [div_round numerator divisor] rounds half away from zero for any positive
    divisor. An exact half cannot occur for an odd divisor, so the rule stays
    well defined there too. *)
let div_round numerator divisor =
  if divisor <= 0L then Serror.fail "divisor must be positive"
  else if numerator = Int64.min_int then Serror.fail "integer overflow"
  else
    let negative = numerator < 0L in
    let magnitude = if negative then Int64.neg numerator else numerator in
    let quotient = Int64.div magnitude divisor in
    let remainder = Int64.rem magnitude divisor in
    let half = Int64.div divisor 2L in
    let round_up =
      if Int64.rem divisor 2L = 0L then Int64.compare remainder half >= 0
      else Int64.compare remainder half > 0
    in
    let rounded = if round_up then Int64.add quotient 1L else quotient in
    Ok (if negative then Int64.neg rounded else rounded)

(** [div_ceil numerator divisor] rounds a nonnegative numerator up. Used for
    margin reservation, so a capital check never under-reserves. *)
let div_ceil numerator divisor =
  if divisor <= 0L then Serror.fail "divisor must be positive"
  else if numerator < 0L then Serror.fail "numerator must be nonnegative"
  else
    let quotient = Int64.div numerator divisor in
    let remainder = Int64.rem numerator divisor in
    if remainder = 0L then Ok quotient else Ok (Int64.add quotient 1L)

(** [notional ~price_ticks ~quantity_units] is the trade notional in money
    units under the declared rounding rule. *)
let notional ~price_ticks ~quantity_units =
  if price_ticks <= 0L then Serror.fail "price ticks must be positive"
  else mul_div ~divisor:notional_divisor price_ticks quantity_units

let bps ~money ~bps =
  if bps < 0 then Serror.fail "basis points must be nonnegative"
  else mul_div ~divisor:bps_divisor money (Int64.of_int bps)
