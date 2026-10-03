# JevLike technical stack and deployment plan

Owner: `lucyrunner`. This page is the current implementation direction for the HiPerGator JevLike
workstream. The old Laya-first description is superseded here. Historical team handoffs elsewhere
retain their original date and author.

## Product target

Build **JevLike**, an open-source one-pass choice model. Its first interface is a text context plus
a caller-supplied list of two or more text options, returning a full categorical probability vector
in the same option order. The implementation is based on the MIT-licensed
[`vinnylarouge/jevlike`](https://github.com/vinnylarouge/jevlike) source vendored in [`jevlike/`](jevlike/)
at commit `94f5fd1b0b11d52bbdfdf4e0ee6aa96b568f8452`.

JevLike is an independent open alternative with a similar one-pass choice interface. It is not
TypeSafe's closed Jev implementation. The upstream repository describes a small byte encoder and an
optional frozen Hugging Face encoder feeding an option-attention scorer. Its README expressly says
it did not match Jev quality or reproduce TypeSafe's private training method. We do **not** claim
that JevLike implements or reproduces RLCD. We will add calibration-aware objectives only as
separately specified and evaluated extensions.

The `council/` and `cpp/` packages are downstream fusion runtimes. A first native C++ scorer now
supports exported tiny-byte-encoder checkpoints. Its Slurm workflow includes synthetic training,
export, compilation, and probability parity; a successful HPG run is still required before calling
the path verified on HiPerGator.

## Language choices by subsystem

| Subsystem | Chosen stack | Why and boundary |
|---|---|---|
| JevLike training and research | Python, PyTorch, JSONL, HPG Slurm | The upstream model and trainer are PyTorch. HPG documents configured PyTorch environments. Python is kept off the request path; it remains the practical training/experiment interface. |
| Data prep and calibration research | Python plus SQL and versioned data artifacts | Existing ingestion and evaluation work is Python/SQL. Keep it batch-oriented and preserve availability timestamps, case identity, hashes, and chronological splits. |
| Council, feature transforms, risk checks | C++17 | The native C++ probability contract already exists, has a working HPG batch build, and supports calibration, gating, fusion, joint state metadata, and bounded parallel specialists. Keep allocations bounded and avoid unnecessary model copies. |
| Neural inference optimization | ONNX Runtime C++ first; TensorRT only after parity and device benchmarks | Export the upstream model with dynamic batch and option dimensions. Verify output parity over varied option counts and text lengths. Use TensorRT only on compatible NVIDIA deployments when measured p95/p99 improves after transfer and batching costs. |
| Network API/control plane | Rust with Tokio, as a thin service around the C++ engine | Use Rust for request validation, auth, bounded queues, cancellation, rate limits, health checks, and async network I/O. Keep model math in C++; communicate through a narrow C ABI or one local IPC hop after benchmarking. Do not add Rust to the training loop. |
| Quantum experiments | Python quantum SDKs and simulators, offline | Keep QCBM/QAOA and eligible kernel experiments in reproducible research jobs. Only pass validated outputs or scenario artifacts to the council. A simulator is classical execution; a QPU is a separately measured backend, not an HPG GPU. |
| Julia | Not in the initial product stack | Julia is capable for numerical work, but this project has no unique Julia-only workload that justifies a second statistical runtime and artifact bridge. Reconsider only if a named model beats the existing Python/C++ baseline at equal budgets. |
| UI/demo | Thin TypeScript web client, later | The product's evidence is its predictions and measurements. Add a UI after stable inference and artifact contracts exist. |

Python therefore remains part of the build. The low-latency serving path is designed to use native
C++ inference, with a Rust network layer when there is a measured reason to expose a concurrent
service. No language is accepted because it sounds fast: record batch size, warm/cold state, hardware,
model and tokenizer hashes, p50/p95/p99, throughput, memory, and score parity for each runtime.

## HiPerGator and Vultr roles

**HiPerGator** owns batch model training, architecture/parameter sweeps, calibration and fusion
experiments, large scenario simulation, quantum simulators, and reproducible Slurm evaluation. Start
with synthetic CPU jobs; request GPUs and multi-node resources only for a measured workload. UFIT-RC
documents preconfigured PyTorch modules and requires explicit GPU/partition requests for GPU jobs.

**Vultr** is the cloud deployment and external-serving counterpart: deploy the pinned JevLike model
and C++ council as a GPU-backed prediction service, expose a narrow probability API, and measure
real request latency/throughput and operating cost. Use Vultr compute for serving and, when credits
and a real experiment justify it, GPU scenario simulation. HPG-trained artifacts should move as
versioned, hashed releases; the deployed endpoint must identify its model, data, tokenizer, and
calibration versions. Do not put HPG account credentials or sponsor API keys in Git. Verify HPG
egress, Vultr account/credit terms, region, GPU inventory, and ongoing cost before provisioning.

This split connects the systems through reproducible model artifacts and measured service behavior.
It does not put a WAN call between HPG and an action, require a quantum circuit in an interactive
request, or treat extra compute as evidence of forecast quality. Keep QPU access and queue time out
of the normal serving path.

Public Gator Quant Hacks pages list **Best Use of Vultr** as an MLH sponsor prize and describe
Vultr compute/GPU use. The public Devpost rules also say teams submit to one main track; the detailed
Hacker Guide controls track eligibility. Treat Vultr as a sponsor award layered onto the team's
registered main track unless the organizers confirm otherwise. A credible demonstration is a live
Vultr deployment of the trained JevLike probability API with its real resource, latency, reliability,
and cost measurements—not a logo or an unmeasured cloud VM.

## Work sequence and gates

1. Keep the upstream MIT attribution and pin the exact source commit.
2. Run the upstream synthetic quickstart; save configuration and artifact hashes outside Git.
3. Confirm score parity between Python and the C++ inference/export path across candidate counts,
   Unicode/options, truncation boundaries, and batching. Failed or unsupported inputs must return
   explicit errors or abstention.
4. Add a public, licensed target dataset with point-in-time provenance and entity/time-disjoint
   train, validation, calibration, gate, and final evaluation windows. Keep the competition OOS
   sealed under [`docs/brief.md`](../../docs/brief.md).
5. Compare JevLike with prevalence, linear/logistic, tree, and frozen-encoder baselines using log
   loss, Brier score, calibration, robustness, latency, and resource budgets.
6. Admit a specialist to the council only when its versioned forecast contract and out-of-sample
   evidence are complete. Test every added Bayesian, quantum, or scenario method against an
   equal-budget classical baseline.
7. Deploy the same pinned artifact on Vultr and benchmark end-to-end. Record cold start, p50/p95/p99,
   requests per second, GPU/CPU/memory use, errors, and cost per request. Compare against local C++
   and HPG batch inference. No production trading or live order path is included in this workstream.

## Current scope

The current code has a C++ council and tiny-model scorer, Python calibration/fusion reference,
vendored JevLike model, export format, and an HPG Slurm train/evaluate/export/parity workflow. The
workflow has not yet been submitted or verified. There is no usable target decision dataset,
calibrated domain model, Rust API, Vultr deployment, or QPU access. These remain build gates, not
assumed capabilities.

## Primary technical references

- [JevLike upstream README and MIT license](https://github.com/vinnylarouge/jevlike)
- [UF HiPerGator PyTorch support](https://docs.rc.ufl.edu/domain/computer_vision/)
- [UF HiPerGator PyTorch GPU job requirements](https://docs.rc.ufl.edu/software/apps/pytorch/usage/)
- [PyTorch dynamic ONNX export](https://docs.pytorch.org/docs/main/onnx_export.html)
- [ONNX Runtime C++ API](https://onnxruntime.ai/docs/get-started/with-cpp.html)
- [NVIDIA TensorRT C++ API](https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/c-api-docs.html)
- [Tokio asynchronous Rust runtime](https://tokio.rs/)
- [Vultr GPU instance provisioning](https://docs.vultr.com/products/compute/instances/cloud-gpu/provisioning)
- [Gator Quant Hacks Devpost](https://gqhacks.devpost.com/) and [MLH prize listing](https://www.mlh.com/events/gator-quant-hacks/prizes)
