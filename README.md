# Impreza Platform Agent

Public installer and binaries for the Impreza Platform agent.
Current stable version: **0.6.1**, available for Linux amd64 and arm64.

## New installations

Use the installation command provided by the My Apps portal. It includes a
single-use bootstrap token that registers this server to your account.
The installer verifies the release checksum before installing the executable.

## Update an existing agent

Check the installed and stable versions:

```sh
curl -fsSL https://raw.githubusercontent.com/imprezahost/agent-public/main/update.sh | sudo sh -s -- --check
```

After all deployment operations have finished, update:

```sh
curl -fsSL https://raw.githubusercontent.com/imprezahost/agent-public/main/update.sh | sudo sh -s -- --apply
```

No bootstrap token is required. This works with older agents, including 0.5.1.
The updater checks SHA-256 and embedded version before replacing the binary,
restarts only the agent and restores the previous executable if startup fails.
Credentials, configuration and application containers are preserved. Confirm
the new version in the portal after its next heartbeat. A running local service
is not proof that the API can be reached. Wait for all deployments to finish
before updating; this command does not drain the command queue.

Use IMPREZA_AGENT_VERSION to pin a numeric version; downgrades are refused.
Custom executable/service paths require a manual update.

## Release files

- releases/stable/version.txt identifies the stable release.
- releases/stable/0.6.1/ contains versioned binaries and .sha256 checksums.
- releases/stable/latest/ provides the installer-compatible stable alias.
- update.sh supports --check and --apply, with concurrent-update protection.

Agent 0.6.0 prepares images before replacement and supports retained-release
recovery. Manual app rollback requires compatible API support and a retained
release; it does not revert database contents or mutable data.

Agent 0.6.1 deploys the exact Git commit supplied by a webhook or build context.
If the requested revision cannot be fetched and verified, it fails before
replacing containers. Deployments without a commit continue to follow the branch.
