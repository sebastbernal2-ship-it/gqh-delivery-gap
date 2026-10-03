# HiPerGator access setup

Owner: zifeiliu. This is an access/setup handoff, not a compute approach. Keep job code and
approach-specific environments in their own `hpc/<approach>/` directories.

## Status

- **Account access: verified by owner.** Login from the owner's Mac succeeded with password and
  Duo using the `hpg` SSH shortcut.
- **Blue storage: assigned, not independently checked here.** The owner reports a project Blue
  directory. Its account-specific path is deliberately not recorded in this public repository;
  keep it in local shell configuration as `HPG_BLUE_DIR`.
- **Mac-to-HiPerGator key login: verified 2026-10-03.** The dedicated Mac public key was installed
  with `ssh-copy-id`. Key authentication succeeded; interactive SSH then required Duo. The private
  key is encrypted and must be loaded into the SSH agent before the client can sign with it.
- **HTTP API: no general key identified.** SSH access and the AI Gateway key are different
  credentials. Identify the specific service and endpoint before looking for an API credential.

These setup facts do not establish that external data has been downloaded. The synthetic CPU pilot
has run on HiPerGator; see [its approach README](../probabilistic-council/README.md) for the job
record. Do not put passwords, Duo codes, private keys, API keys, or account-specific storage paths
in the repository.

## Mac-side SSH key setup

The owner's current Mac key setup is verified. For a future Mac or key rotation, use the steps below.

Run these commands on the Mac, not in an SSH session:

```sh
ls -l ~/.ssh/id_ed25519_hpg*
```

If both the private key and `.pub` file exist, install the public key on the HiPerGator account
(the variable should contain the owner's HiPerGator username):

```sh
ssh-copy-id -i ~/.ssh/id_ed25519_hpg.pub "${HPG_USERNAME}@hpg.rc.ufl.edu"
```

Then test `ssh hpg`; Duo remains required after key authentication. If the dedicated Mac key pair
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

This page records the owner's verified SSH setup and the remaining storage/API checks. Blue storage
access from a job and HTTP API access remain unverified; keep credentials and data out of Git.
