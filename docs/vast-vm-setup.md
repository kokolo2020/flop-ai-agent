# Vast.ai VM preparation

Prepared 2 November 2026. This guide prepares access and host diagnostics; it does
not rent hardware, install a miner or establish FLOP admission.

## Prepare the account before a rental

Vast's [VM guide](https://github.com/vast-ai/docs/blob/main/linux-virtual-machines.mdx)
documents the Ubuntu 22.04 **VM** template, SSH launch mode and adding an SSH
public key before the VM starts. A regular Docker template is a different
environment. Confirm the offer explicitly supports the chosen VM template.

1. On the computer that will administer the VM, identify an existing SSH public
   key you control, or create a dedicated passphrase-protected Ed25519 key there.
   Keep the private key on that computer and back it up privately.
2. Add only the public `.pub` key to Vast's account SSH keys. No private key or
   FLOP signer belongs in the template, account notes or chat.
3. Open Templates and select the Ubuntu VM template with SSH access. Keep the
   on-start script empty during preparation; do not auto-start miner software.
4. Record the chosen template and candidate offer. Check GPU count, CPU
   architecture, disk allocation, hourly/storage/bandwidth charges and the
   provider's termination procedure. Do not create an instance until the rental
   budget and purpose are agreed. Operator access is still needed for FLOP work.

## First connection after an authorized VM is created

Use Vast's Connect details for the actual username, hostname and SSH port. Verify
the VM's SSH host fingerprint through a trusted host/provider channel first;
`ssh-keyscan` alone does not authenticate it. Configure a local SSH alias:

```sshconfig
Host flop-vast
    HostName REPLACE_WITH_VM_HOST
    User REPLACE_WITH_VM_USER
    Port REPLACE_WITH_VM_SSH_PORT
    IdentityFile ~/.ssh/REPLACE_WITH_YOUR_PRIVATE_KEY_FILENAME
    IdentitiesOnly yes
    ForwardAgent no
    StrictHostKeyChecking yes
```

This is an incomplete local example. Never commit your real SSH configuration or
private keys. Add the independently verified host key to local `known_hosts`.
Unlock a passphrase-protected key in your local SSH agent before the batch probe.

From the updated ComputePilot checkout on that administration computer:

```bash
python3 -m computepilot.miner_test ssh-preflight \
  --host flop-vast --target h100-nvl \
  --out miner-results/vast-first-check.json
```

For the 80 GB PCIe card select `--target h100-pcie`; for A40 use `a40`. The probe
streams its standard-library Python code over SSH, installs nothing and does not
start a container without an explicit `--cuda-image`. It needs Python 3 already
available on the VM. Missing prerequisites produce exit 2 with an incomplete
report. The initial Docker GPU check remains NOT_RUN, so this first pass cannot
grant full host readiness.

Review the sanitized report for Linux amd64, the actual single GPU, usable VRAM,
free disk, Docker daemon, Compose and NVIDIA runtime. If components are missing,
prepare installation steps for that actual OS/driver combination before changing
the VM. Do not infer GPU-container access from host `nvidia-smi` alone.

After approving a CUDA diagnostic image with its exact digest, repeat with a
new output filename:

```bash
python3 -m computepilot.miner_test ssh-preflight \
  --host flop-vast --target h100-nvl \
  --cuda-image APPROVED_CUDA_IMAGE@sha256:REPLACE_WITH_64_HEX_DIGEST \
  --out miner-results/vast-container-check.json
```

The image argument above is deliberately invalid until replaced. This second
probe can pull the image and run a short, network-disabled GPU diagnostic
container; allow disk/time for that test. It never starts FLOP services.

## What the H100 profiles mean

| ComputePilot target | Accepted inventory name | Minimum reported memory |
| --- | --- | --- |
| `h100-pcie` | `H100 PCIe`, optionally prefixed `NVIDIA` | 74,000 MiB |
| `h100-nvl` | `H100 NVL`, optionally prefixed `NVIDIA` | 88,000 MiB |

These conservative thresholds are local diagnostic heuristics with memory
headroom; they are not a miner calibration or performance guarantee. Names are
matched case-insensitively. Multiple cards, MIG inventories, an unexpected name
or inadequate VRAM fail the selected profile for review. In particular, an SXM
card is not silently treated as PCIe. See [NVIDIA's H100 specifications](https://www.nvidia.com/en-us/data-center/h100/).

Both the Python collector and browser viewer keep protocol compatibility and
activation separate from a passing host check. Import only sanitized reports
into the readiness viewer; never upload the access bundle or private env.

Use the [November FLOP preparation checklist](mining-readiness-2026-11-02.md)
for approved network/release/model inputs and subsequent evidence. A Vast
listing, a Docker pass or the presence of an H100 establishes none of those
gates. Stop provider billing using its termination controls when the agreed test
ends; stopping a process is not a billing shutdown.
