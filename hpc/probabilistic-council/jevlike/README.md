# JevLike model core

This directory vendors the model package from [vinnylarouge/jevlike](https://github.com/vinnylarouge/jevlike)
at upstream commit `94f5fd1b0b11d52bbdfdf4e0ee6aa96b568f8452`. Upstream source files and its MIT license
are retained. Local extensions should be documented here and kept compatible with the upstream JSONL
choice format unless the product contract is deliberately versioned.

JevLike scores a supplied context against a supplied, variable-length set of text options in one
forward pass. The output is a categorical distribution over exactly that option set; it does not
generate a free-form answer. The package contains a small byte-encoder scorer and an optional frozen
Hugging Face encoder. It is an independent Jev-like implementation, not TypeSafe's model, and its
published training method is not claimed to reproduce RLCD.

## Product boundary

- This upstream package is the model/training baseline.
- `../council/` and `../cpp/` provide calibrated multi-specialist fusion. They do not replace the
  one-pass JevLike scorer.
- First bring up a reproducible tiny-encoder run on synthetic data. Then adapt one owned, permitted,
  point-in-time decision dataset and compare against a frozen-encoder and classical baseline.
- A returned softmax is a probability vector, not evidence of calibration. Fit and evaluate
  calibration on separate, chronological partitions before using it downstream.

The stack decision, Vultr integration plan, and deployment gates are in
[`../STACK.md`](../STACK.md). Upstream source/license metadata must be preserved in derivative
distributions. Pretrained checkpoints and datasets have independent terms; none are bundled here.

## Local correctness changes

`trainable_state()` detaches, moves to CPU and **clones** each trainable tensor. The clone owns
its storage: later optimizer steps cannot overwrite an earlier best-validation snapshot on CPU.
Frozen encoder parameters remain excluded, preserving the upstream checkpoint format.
The regression suite exercises actual training with a controlled worsening validation sequence
and verifies the reloaded checkpoint matches the earlier winning epoch exactly.

See [the component validation record](../VALIDATION.md) for tests and limitations.
