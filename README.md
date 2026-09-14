# Impreza Platform Agent

Public installer and binaries for the Impreza Platform agent.
Current stable version: **0.6.7**, available for Linux amd64 and arm64.

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
- releases/stable/0.6.7/ contains versioned binaries and .sha256 checksums.
- releases/stable/latest/ provides the installer-compatible stable alias.
- update.sh supports --check and --apply, with concurrent-update protection.

Agent 0.6.0 prepares images before replacement and supports retained-release
recovery. Manual app rollback requires compatible API support and a retained
release; it does not revert database contents or mutable data.

Agent 0.6.1 deploys the exact Git commit supplied by a webhook or build context.
If the requested revision cannot be fetched and verified, it fails before
replacing containers. Deployments without a commit continue to follow the branch.

Agent 0.6.2 reports unsupported commands as failures instead of simulated
success. It performs no operation for those commands and continues polling.
Queued agent upgrades remain unsupported; use the update command above.

Agent 0.6.3 supports opt-in required healthy startup. Generated Node deployments can set `require_healthy_start: true` with an explicit `healthcheck_path` and `startup_timeout_seconds` from 30 to 600 (default 60). The first deployment fails if it does not become healthy; named volumes are preserved. Retained releases keep their own startup policy for automatic recovery and manual rollback. Older agents must be updated explicitly before using this option. See [deployment settings](https://docs.imprezahost.com/tutorials/agent-apps-panels.html#required-startup).

## Runtime observations

Agent 0.6.4 reports recent container state separately from the last deployment result. Missing or stale observations remain unknown. A running container without a healthcheck is not declared healthy. The report contains bounded counts and timestamps, without environment variables or healthcheck logs. Update existing servers explicitly using the command above. See [runtime health](https://docs.imprezahost.com/runtime-health.html).


## Deployment cancellation

Agent 0.6.5 supports cancellation at preparation checkpoints. The current
pull/build step finishes before cancellation is confirmed and configuration
is restored. Existing containers are not replaced. Replacement and recovery
cannot be cancelled; interrupted agents require operation reconciliation.
Update only after current operations finish. See [deployment cancellation](https://docs.imprezahost.com/deployment-cancellation.html).

## Deployment progress and saved results

Agent 0.6.6 reports the current deployment step and saves final operation results before delivery. After a restart, saved results are resent without repeating the deployment. Agent 0.6.7 adds verified preparation reconciliation as described below; other interrupted execution requires support. Preserve the private agent state directory. Existing agents update explicitly after active operations finish. See [deployment progress](https://docs.imprezahost.com/deployment-progress.html).

## Interrupted preparation

Agent 0.6.7 persists the previous preparation configuration and completion checkpoints. After restart, it can verify an unstarted operation or completed preparation, restore configuration with unchanged container identities and close the interrupted attempt without executing it again. Wait for the final failure or confirmed cancellation before retrying explicitly. Busy external work, missing checkpoints, container drift and replacement uncertainty remain blocked for support review. It does not resume or kill Docker builds, restore application data or update the fleet automatically. Existing operations do not gain checkpoints retroactively. See [preparation reconciliation](https://docs.imprezahost.com/deployment-progress.html#preparation-recovery).
