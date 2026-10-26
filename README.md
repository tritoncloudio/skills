# Triton Cloud Skill

An agent skill for Triton Cloud: run code in sandboxes and manage tenant resources with `tritonctl`, the Python and TypeScript sandbox SDKs, the MCP server and the Cloud API.

## Installation

### Skills

```bash
npx skills add https://github.com/tritoncloudio/skills --skill tritoncloud
```

### Claude Code (plugin)

```bash
claude plugin marketplace add tritoncloudio/skills
claude plugin install tritoncloud@tritoncloud --scope user
```

Scope options: `user` (all projects), `project` (shared via git), `local` (gitignored).

### Manual

Copy `skills/tritoncloud` into your agent's skills directory:

| Agent | Skill directory |
| :--- | :--- |
| Claude Code | `~/.claude/skills/` |
| Cursor | `~/.cursor/skills/` |
| OpenCode | `~/.config/opencode/skills/` |
| OpenAI Codex | `~/.codex/skills/` |
| Windsurf | `~/.windsurf/skills/` |

## Usage

The skill loads when a request involves Triton Cloud, `tritonctl` or Triton sandboxes. The agent still needs `tritonctl` installed and signed in; the skill tells it how to check.

## Structure

```text
skills/tritoncloud/
├── SKILL.md            # Entry point, written by hand
└── references/         # Generated
    ├── cli/            # tritonctl commands and flags, from `tritonctl llms-full.txt`
    ├── api/            # Cloud API operations and schemas, from the OpenAPI document
    ├── sdk/            # Python SDK, TypeScript SDK, MCP server
    ├── guides/         # Sandbox quickstart, GitHub workflows
    └── SOURCE.md       # tritonctl version and source revision
```

## Updating the references

Everything under `references/` comes from [mariana-trench](https://github.com/TritonDataCenter/mariana-trench). A weekly workflow regenerates it and opens a pull request when it changed. It needs a `MARIANA_READ_TOKEN` secret with read access to mariana-trench, its submodules and its private git dependencies. The token is used only to fetch; the build runs offline in a read-only job with no secrets.

To run it locally (needs Rust, Python 3.10 or later, and read access to mariana-trench):

```bash
scripts/update-references.sh
```

With an existing checkout and binary, skip the clone and build:

```bash
MARIANA_DIR=../mariana-trench TRITONCTL=$(command -v tritonctl) scripts/update-references.sh
```

`SKILL.md` is not generated. Update it when a change in tritonctl or the SDKs makes it wrong.

## License

Mozilla Public License 2.0. See [LICENSE](LICENSE).
