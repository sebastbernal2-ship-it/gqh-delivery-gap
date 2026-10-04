(** Exact decimal conversion for venue tick and lot units. *)

type scale = { decimals : int; factor : int64; step_units : int64 }

type instrument = {
  symbol : string;
  price : scale;
  quantity : scale;
}

let ( let* ) result f = Result.bind result f

let failf format = Serror.failf format

let digits value =
  if value = "" || String.exists (fun char -> char < '0' || char > '9') value then
    failf "invalid decimal digits"
  else
    let rec loop index total =
      if index = String.length value then Ok total
      else
        let digit = Int64.of_int (Char.code value.[index] - Char.code '0') in
        if total > Int64.div (Int64.sub Int64.max_int digit) 10L then
          failf "decimal value overflows int64"
        else loop (index + 1) Int64.(add (mul total 10L) digit)
    in
    loop 0 0L

let split_decimal value =
  if value = "" || value.[0] = '-' || value.[0] = '+' then
    failf "decimal must be unsigned"
  else
    match String.index_opt value '.' with
    | None -> Ok (value, "")
    | Some dot ->
        if String.index_from_opt value (dot + 1) '.' <> None then
          failf "decimal has multiple points"
        else
          let whole = String.sub value 0 dot in
          let fraction =
            String.sub value (dot + 1) (String.length value - dot - 1)
          in
          let whole = if whole = "" then "0" else whole in
          if fraction = "" then failf "decimal has no fractional digits"
          else Ok (whole, fraction)

let trim_trailing_zeros value =
  let rec last_nonzero index =
    if index < 0 then -1
    else if value.[index] <> '0' then index
    else last_nonzero (index - 1)
  in
  let last = last_nonzero (String.length value - 1) in
  if last < 0 then "" else String.sub value 0 (last + 1)

let pow10 decimals =
  if decimals < 0 || decimals > 18 then failf "decimal precision is out of range"
  else
    let rec loop count result =
      if count = decimals then Ok result
      else if result > Int64.div Int64.max_int 10L then
        failf "decimal scale overflows int64"
      else loop (count + 1) Int64.(mul result 10L)
    in
    loop 0 1L

let scaled_value ~decimals ~factor whole fraction =
  let* whole_units = digits whole in
  let fraction =
    if String.length fraction > decimals then
      let extra = String.sub fraction decimals (String.length fraction - decimals) in
      if trim_trailing_zeros extra <> "" then
        raise (Invalid_argument "fraction has too many nonzero digits")
      else String.sub fraction 0 decimals
    else fraction ^ String.make (decimals - String.length fraction) '0'
  in
  let* fraction_units = if fraction = "" then Ok 0L else digits fraction in
  if whole_units > Int64.div (Int64.sub Int64.max_int fraction_units) factor then
    failf "decimal value overflows int64"
  else Ok Int64.(add (mul whole_units factor) fraction_units)

let strip_leading_zeros value =
  let rec first_nonzero index =
    if index = String.length value then index
    else if value.[index] = '0' then first_nonzero (index + 1)
    else index
  in
  let index = first_nonzero 0 in
  if index = String.length value then "0"
  else String.sub value index (String.length value - index)

let canonical_decimal value =
  let* whole, fraction = split_decimal value in
  let whole = strip_leading_zeros whole in
  let fraction = trim_trailing_zeros fraction in
  if fraction = "" then Ok whole else Ok (whole ^ "." ^ fraction)

let compare_decimal left right =
  match (canonical_decimal left, canonical_decimal right) with
  | Ok left, Ok right ->
      let split value =
        match String.index_opt value '.' with
        | None -> value, ""
        | Some index ->
            String.sub value 0 index,
            String.sub value (index + 1) (String.length value - index - 1)
      in
      let left_whole, left_fraction = split left in
      let right_whole, right_fraction = split right in
      let by_length = Int.compare (String.length left_whole) (String.length right_whole) in
      if by_length <> 0 then by_length
      else
        let by_whole = String.compare left_whole right_whole in
        if by_whole <> 0 then by_whole
        else
          let rec compare_fraction index =
            if index = String.length left_fraction && index = String.length right_fraction then 0
            else
              let left_digit =
                if index < String.length left_fraction then left_fraction.[index] else '0'
              in
              let right_digit =
                if index < String.length right_fraction then right_fraction.[index] else '0'
              in
              let comparison = Char.compare left_digit right_digit in
              if comparison <> 0 then comparison else compare_fraction (index + 1)
          in
          compare_fraction 0
  | Error error, _ | _, Error error -> invalid_arg error

let scale_of_step value =
  try
    let* whole, fraction = split_decimal value in
    let fraction = trim_trailing_zeros fraction in
    let decimals = String.length fraction in
    let* factor = pow10 decimals in
    let* step_units = scaled_value ~decimals ~factor whole fraction in
    if step_units <= 0L then failf "decimal step must be positive"
    else Ok { decimals; factor; step_units }
  with Invalid_argument message -> Serror.fail message

let instrument ~symbol ~price_step ~quantity_step =
  if symbol = "" then failf "instrument symbol must not be empty"
  else
    let* price = scale_of_step price_step in
    let* quantity = scale_of_step quantity_step in
    Ok { symbol; price; quantity }

let to_units scale value =
  try
    let* whole, fraction = split_decimal value in
    let* units = scaled_value ~decimals:scale.decimals ~factor:scale.factor whole fraction in
    if Int64.rem units scale.step_units <> 0L then
      failf "decimal value is not aligned to venue step"
    else Ok (Int64.div units scale.step_units)
  with Invalid_argument message -> Serror.fail message

let to_price_ticks instrument value = to_units instrument.price value
let to_quantity_lots instrument value = to_units instrument.quantity value
