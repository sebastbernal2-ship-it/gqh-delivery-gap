# HiPerGator access setup

Owner: zifeiliu. This is an access/setup handoff, not a compute approach. Keep job code and
approach-specific environments in their own `hpc/<approach>/` directories.

## Status

- **Account access: verified by owner.** Login from the owner's Mac succeeded with password and
  Duo using the `hpg` SSH shortcut.
- **Blue storage: assigned, not independently checked here.** The owner reports a project Blue
  directory. Its account-specific path is deliberately not recorded in this public repository;
  keep it in local shell configuration as `HPG_BLUE_DIR`.
- **Mac-to-HiPerGator key login: not verified.** A key generated on HiPerGator and `ssh-copy-id`
  run from there do not install the Mac's public key on the account. Current `ssh hpg` login still
  asks for password and Duo.
- **HTTP API: no general key identified.** SSH access and the AI Gateway key are different
  credentials. Identify the specific service and endpoint before looking for an API credential.

These are reported setup facts, not evidence that data has been downloaded or that a compute job
has run. Do not put passwords, Duo codes, private keys, API keys, or account-specific storage paths
in the repository.

## Next: verify Mac-side SSH key setup

Run these commands on the Mac, not in an SSH session:

```sh
ls -l ~/.ssh/id_ed25519_hpg*
```

If both the private key and `.pub` file exist, install the public key on the HiPerGator account
(the variable should contain the owner's HiPerGator username):

```sh
ssh-copy-id -i ~/.ssh/id_ed25519_hpg.pub "${HPG_USERNAME}@hpg.rc.ufl.edu"
```

Then test `ssh hpg`. Record whether password/Duo is still required. If the dedicated Mac key pair
does not exist, create it on the Mac before copying its public key; do not overwrite an existing
key. Never copy or commit the private key. If only one of the two files exists, inspect the local
SSH setup before generating or replacing anything.

## Storage and API follow-up

Set `HPG_BLUE_DIR` in an untracked, local shell config to the assigned Blue directory. Confirm it
from an authenticated HiPerGator session before using it in job scripts. Do not put a personal
absolute path in tracked files; scripts should read `HPG_BLUE_DIR` from the environment.

For HTTP access, first name the required API product/service and endpoint. Request a credential only
through that service's documented process, store it outside Git, and do not treat SSH keys or AI
Gateway credentials as interchangeable with an HTTP API key.

## Evidence boundary

This page records the owner's reported state and the next verification steps. It does not claim
that Mac key authentication, Blue storage access from a job, an HTTP API, or a HiPerGator workload
has been tested. When those checks are done, update this page with the command or test outcome and
any non-sensitive limitation; keep credentials and data out of Git.
