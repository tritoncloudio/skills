---
name: tritoncloud
description: Runs code in Triton Cloud sandboxes (Linux microVMs for agents) and manages Triton Cloud tenant resources (instances, VPCs, subnets, firewall rules, load balancers, disks, filesystems, images) with the tritonctl CLI, the Python and TypeScript sandbox SDKs, the MCP server, or the Cloud API. Use when a task mentions Triton Cloud, tritonctl, triton_sandbox, @triton/sandbox, or needs an isolated sandbox or a VM on Triton.
---

## What Triton Cloud gives you

- **Sandboxes**: Linux microVMs with their own kernel. They start from a warm pool, run commands, hold files, and expose ports over an authenticated tunnel. Snapshot, fork, stop/start and pause/resume are built in. The SDK surface follows E2B.
- **Instances and networking**: VMs in a project, inside VPCs with subnets, firewall rules, route tables, NAT gateways, floating and external IPs, load balancers, disks and shared NFS filesystems.

Everything belongs to a **tenant** and lives in a **project**. Your administrator gives you the API endpoint, a user name and a project.

## Before you start

1. **tritonctl installed?** Run `tritonctl --version`. If it is missing, tell the user. There is no binary download yet; it builds from source with `cargo install --locked --path cli/tritonctl` in a mariana-trench checkout (private repo, ask the administrator for access).
2. **Signed in?** Run `tritonctl whoami`. If there is no session:
   ```sh
   tritonctl configure --endpoint <URL> --project <PROJECT> --username <USER> --password-stdin
   ```
   `tritonctl login --sso` signs in through the browser. For CI, use `TRITONCTL_ENDPOINT` with `TRITONCTL_API_KEY` (create one with `tritonctl api-key create`).
3. **Private CA?** Set `TRITON_DC_ANCHORS=<ca.pem>`. tritonctl and both SDKs add it to the default roots.
4. **What is turned on?** Run `tritonctl sandbox capability` (or `Sandbox.capabilities()`). Some features are gated per tenant and answer `403 FeatureDisabled` until an administrator enables them. Do not retry a gated call; tell the user which feature to ask for.

To keep a script away from the user's own session, point `TRITONCTL_CONFIG_DIR` at a temporary directory.

## tritonctl essentials

```sh
tritonctl sandbox create --name dev --package sandbox-2g --ttl 1h   # waits until running
tritonctl sandbox exec dev -- uname -a                               # exit status is the program's
tritonctl sandbox exec dev --cwd /work --env K=V --max-duration 10m -- make test
tritonctl sandbox exec dev -q --cmd 'ls /work | wc -l'               # shell line, output only
tritonctl sandbox fs put dev ./data.csv /work/data.csv
tritonctl sandbox fs get dev /work/out.json ./out.json
tritonctl sandbox list -j
tritonctl sandbox delete -y dev
```

Rules for driving tritonctl from an agent:

- **Parse JSON, not tables.** `-j` (or `--format json`) is the stable interface.
- **Pass `-y` to anything that changes or deletes.** Without a terminal and without `-y`, the command exits 2. Where a command offers `-n` (`--dry-run`), it prints the plan and stops.
- **Do not use `exec -t -i`** from a script; it is for an interactive terminal.
- **Always give a sandbox a short `--ttl`** so nothing is left running if the script dies. `tritonctl sandbox keepalive dev --ttl 1h` moves the deadline; `--on-deadline stop|pause|delete` picks what happens.
- **Name what you create** (`--name`) and refer to it by that name, not by a uuid prefix that can match two things.
- **Read before you change**: `show -j` before `update`, `network show` before `network replace` (replace sets the whole policy).
- For a long run, `exec --tag build ...` and later `tritonctl sandbox exec-attach dev build`.

Exit codes: `0` ok, `1` failure, `2` bad usage or a prompt with no terminal, `3` not found, `4` no session or not allowed. `sandbox exec` returns the program's own status (128 plus the signal number for a signal). Errors print to stderr as `tritonctl <command>: error (<Code>): <message>`; `-v` adds the cause chain.

`tritonctl llms.txt` and `tritonctl llms-full.txt` print the guide and every flag of the installed version. Prefer them over this skill when they disagree.

## Sizing

A **package** sets the size of a sandbox; numbers for CPU or memory are refused, and the error names the packages you may use.

| Package | vCPU | Memory | Disk |
|---|---|---|---|
| `sandbox-2g` (default) | 2 | 2 GiB | 8 GiB |
| `sandbox-4g` | 2 | 4 GiB | 16 GiB |
| `sandbox-8g` | 4 | 8 GiB | 32 GiB |

Your administrator can change this set. To resize, stop the sandbox, then `tritonctl sandbox resize dev --package sandbox-4g`. The disk never shrinks.

## Network

Sandbox egress is **denied by default**. Open it per sandbox:

```sh
tritonctl sandbox create --name web --allow-out 203.0.113.0/24
tritonctl sandbox create --name gh --allow-out-domain github.com --allow-out-domain '*.github.com'   # gated
tritonctl sandbox network show web -j
tritonctl sandbox network replace web --allow-out 203.0.113.7/32    # replaces the whole policy
```

Egress needs a NAT gateway and a default route in the project's VPC; without one the policy is refused. Private and internal ranges are always refused. A name not in `allow_out_domains` does not resolve inside the guest.

## Reaching a port

Start a server in the guest, then forward its port to your machine. The tunnel runs over the API with your own credential.

```sh
tritonctl sandbox exec dev -- python3 -m http.server 8000 --bind 127.0.0.1 &
tritonctl sandbox port-forward dev 8000
curl http://127.0.0.1:8000/
```

Browser preview URLs (`tritonctl sandbox url`, `sbx.get_host()`) are off until the cloud has a preview domain; they fail with "previews are not enabled on this cloud; use port-forward". Use `port-forward` or `sbx.ports.forward()` instead.

`tritonctl sandbox ssh-config dev --install` then `ssh dev.sandbox.triton` gives ssh, scp and VS Code Remote-SSH over the same tunnel.

## Snapshots, forks and templates

```sh
tritonctl sandbox snapshot create dev --name ready
tritonctl sandbox fork dev --count 3 --from-snapshot ready     # filesystem fork
tritonctl sandbox fork dev --count 3 --kind memory             # gated: running processes too
tritonctl sandbox stop dev && tritonctl sandbox start dev      # keeps disk, not memory
tritonctl sandbox pause dev && tritonctl sandbox resume dev    # gated: keeps memory and disk

tritonctl sandbox template build py312 --image docker.io/library/python:3.12-slim --follow
tritonctl sandbox template build devbox --from-snapshot dev/ready
tritonctl sandbox create --name t1 --template py312 --package sandbox-4g
```

If the user will create several sandboxes with the same setup, offer to build a template. Built-in templates: `base`, `code-interpreter`, `desktop`. Only amd64 images build. A memory fork copies whatever secrets are in the parent's memory to every child, so snapshot before loading them.

## GitHub repositories

```sh
tritonctl sandbox create --name app --repo owner/app --branch main   # clones into /work/app
tritonctl sandbox exec app --cwd /work/app -- make test
tritonctl sandbox git app -- switch -c fix
tritonctl sandbox git app -- commit -am "Fix the bug"
tritonctl sandbox pr app --title "Fix the bug" --draft
```

`--repo` needs the egress-domain feature. The token comes from `gh auth token` (or `--github-token-env VAR`, never a flag value) and goes only into the environment of git commands that talk to GitHub. It is not stored in the guest. Use `fetch` then `merge`; `pull` gets no token. `tritonctl sandbox claude --repo owner/app` runs Claude Code in a sandbox.

## SDK essentials: Python

```sh
pip install "git+https://github.com/TritonDataCenter/mariana-trench.git@main#subdirectory=sdks/python"
```

```python
from triton_sandbox import Sandbox

sbx = Sandbox.create(template="code-interpreter", package="sandbox-2g", timeout=600)
try:
    r = sbx.commands.run("echo hello")
    print(r.stdout)
    sbx.files.write("/work/a.txt", "data")
    print(sbx.files.read("/work/a.txt"))
    print(sbx.run_code("1 + 1").text)          # stateful between calls
    with sbx.ports.forward(3000) as fwd:
        print(fwd.local_address)
finally:
    sbx.kill()
```

Credentials, highest first: keyword arguments, then `TRITON_URL` with `TRITON_API_KEY` (or `TRITON_ACCESS_TOKEN`, or `TRITON_USERNAME` and `TRITON_PASSWORD`), `TRITON_PROJECT`, then the tritonctl session. After `tritonctl configure`, the SDK needs no setup. `AsyncSandbox` has the same methods, awaited.

A non-zero exit raises `CommandExitException`. Refusals are typed, all under `SandboxException`: `NotImplementedException` (`.reason`), `NotFoundException`, `RateLimitException` (`.retry_after`), `SandboxNotRunningException`, `QuotaExceededException`, `AuthenticationException`, `PreviewsDisabledException`.

## SDK essentials: TypeScript

`@triton/sandbox` mirrors the Python SDK in camelCase (`runCode`, `timeoutMs`, `ports.forward`, `files.getInfo`). Node 18 or later, or Bun. Not on npm yet; build a tarball with `npm ci && npm pack` in `sdks/typescript` and install it. See [sdk/typescript.md](references/sdk/typescript.md).

## Coming from E2B

Change the import (`from triton_sandbox import Sandbox`) and the credential (`TRITON_URL` + `TRITON_API_KEY`). Differences that matter:

- Egress is denied unless `network=` allows it.
- `files.remove()` refuses a non-empty directory unless `recursive=True`.
- Preview URLs are not enabled yet; use `ports.forward`.
- Desktop streaming is RDP (`tritonctl sandbox rdp`, `desktop.rdp_tunnel()`), not VNC.
- Added: `snapshot()`, `fork(n)`, `stop()`, `start()`, `resize(package)`.

## Instances and networking

The same CLI manages VMs and their network. Each resource has `list`, `show`, `create`, `update` and `delete` where it makes sense; see the CLI reference for flags.

```sh
tritonctl image list -j
tritonctl instance create --help
tritonctl instance list -j
tritonctl vpc list -j && tritonctl subnet list -j
tritonctl firewall-rule list -j
tritonctl nat-gateway create --help       # needed for sandbox egress
tritonctl ssh <instance>                  # over the authenticated tunnel
```

Instance changes are asynchronous: create answers with the instance `pending`, stop with `stopping`. Poll `show -j` until the state you want. An instance can be deleted only when `stopped` or `failed`.

## Quick decision tree

| I need to... | Start here |
|---|---|
| Run code or commands in isolation | [cli/sandbox.md](references/cli/sandbox.md), [sdk/python.md](references/sdk/python.md) |
| Walk through sandboxes end to end | [guides/sandboxes-quickstart.md](references/guides/sandboxes-quickstart.md) |
| Move files in and out | [cli/sandbox-fs.md](references/cli/sandbox-fs.md) |
| Make sandboxes start with my tools | [cli/sandbox-template.md](references/cli/sandbox-template.md) |
| Save state, clone a sandbox | [cli/sandbox-snapshot.md](references/cli/sandbox-snapshot.md), `fork` in [cli/sandbox.md](references/cli/sandbox.md) |
| Open or inspect egress | [cli/sandbox-network.md](references/cli/sandbox-network.md) |
| Reach a guest port | [cli/sandbox-ports.md](references/cli/sandbox-ports.md), `port-forward` in [cli/sandbox.md](references/cli/sandbox.md) |
| Work on a GitHub repo | [guides/sandbox-github.md](references/guides/sandbox-github.md) |
| Give a model sandbox tools over MCP | [sdk/mcp.md](references/sdk/mcp.md) |
| Run a VM | [cli/instance.md](references/cli/instance.md), [cli/image.md](references/cli/image.md) |
| Build the network | [cli/vpc.md](references/cli/vpc.md), [cli/subnet.md](references/cli/subnet.md), [cli/firewall-rule.md](references/cli/firewall-rule.md), [cli/nat-gateway.md](references/cli/nat-gateway.md) |
| Publish a service | [cli/load-balancer.md](references/cli/load-balancer.md), [cli/external-ip.md](references/cli/external-ip.md), [cli/floating-ip.md](references/cli/floating-ip.md) |
| Storage | [cli/disk.md](references/cli/disk.md), [cli/filesystem.md](references/cli/filesystem.md), [cli/storage.md](references/cli/storage.md) |
| Sign in, profiles, API keys | [cli/core.md](references/cli/core.md), [cli/profile.md](references/cli/profile.md), [cli/api-key.md](references/cli/api-key.md) |
| Call the HTTP API directly | [api/README.md](references/api/README.md) |

## Cloud API

The CLI and SDKs are clients of the Cloud API. Call it directly only when neither covers the need.

- Authenticate with `Authorization: Bearer <token>`, where the token is an API key or an access token from `POST /v1/auth/login` (refresh with `POST /v1/auth/refresh`).
- Most collections take `?tenant=&project=` selectors.
- Lists are paginated with `limit` (default 50, at most 500), `page_token` and `sort_by`. Only a missing `next_page` ends the walk.
- Errors are JSON: `{ "error_code", "message", "request_id" }`. Quote `request_id` when reporting a problem.
- Creates honour `Idempotency-Key`, so a retried create returns the same resource.

Per-area operations are in [api/](references/api/README.md); bodies are in [api/schemas.md](references/api/schemas.md).

## Reference index

| Directory | Contents |
|---|---|
| [references/cli/](references/cli/README.md) | Every tritonctl command and flag, by group, plus the agent guide |
| [references/sdk/](references/sdk/) | Python SDK, TypeScript SDK, MCP server |
| [references/guides/](references/guides/) | Sandbox quickstart, GitHub workflows |
| [references/api/](references/api/README.md) | Cloud API operations by tag, and schemas |

The references are generated; [references/SOURCE.md](references/SOURCE.md) names the tritonctl version and source revision they came from.
