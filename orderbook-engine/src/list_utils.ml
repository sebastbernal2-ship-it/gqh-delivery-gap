(** List utility functions. *)

let take n lst =
  let rec aux acc n lst =
    if n <= 0 then List.rev acc
    else
      match lst with [] -> List.rev acc | h :: t -> aux (h :: acc) (n - 1) t
  in
  aux [] n lst
