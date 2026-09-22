# Impreza Platform Agent

Public installer and binaries for the Impreza Platform agent.
Current stable version: **0.6.19**, available for Linux amd64 and arm64.

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
- releases/stable/0.6.19/ contains versioned binaries and .sha256 checksums.
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

Agent 0.6.5 supports cancellation at preparation checkpoints. Without controlled builds enabled, the current
pull/build step finishes before cancellation is confirmed and configuration
is restored. Existing containers are not replaced. Replacement and recovery
cannot be cancelled; interrupted agents require operation reconciliation.
Update only after current operations finish. See [deployment cancellation](https://docs.imprezahost.com/deployment-cancellation.html).

## Deployment progress and saved results

Agent 0.6.6 reports the current deployment step and saves final operation results before delivery. After a restart, saved results are resent without repeating the deployment. Agent 0.6.7 adds verified preparation reconciliation as described below; other interrupted execution requires support. Preserve the private agent state directory. Existing agents update explicitly after active operations finish. See [deployment progress](https://docs.imprezahost.com/deployment-progress.html).

## Interrupted preparation

Agent 0.6.7 persists the previous preparation configuration and completion checkpoints. After restart, it can verify an unstarted operation or completed preparation, restore configuration with unchanged container identities and close the interrupted attempt without executing it again. Wait for the final failure or confirmed cancellation before retrying explicitly. Unsupervised or unconfirmed external work, missing checkpoints, container drift and replacement uncertainty remain blocked for support review. Checkpoint reconciliation does not resume or kill Docker builds, restore application data or update the fleet automatically. Agent 0.6.12 adds the separately enabled controlled-build behavior below. Existing operations do not gain checkpoints retroactively. See [preparation reconciliation](https://docs.imprezahost.com/deployment-progress.html#preparation-recovery).

## Supervised image preparation

Agent 0.6.8 runs pull/build for controlled deployments in a separate supervised process on Linux with systemd. After an agent restart, it waits for the original worker and verifies its durable successful completion receipt before reconciling preparation. It then validates the operation and unchanged containers, restores previous configuration and closes the interrupted attempt as failed or confirms an existing cancellation request. It never repeats the work or the deployment. Missing or invalid receipts, worker failure or timeout, legacy unsupervised work and replacement uncertainty still require support review. Update explicitly after current operations finish. See [supervised preparation](https://docs.imprezahost.com/deployment-progress.html#supervised-preparation).

## Supervised container replacement

Agent 0.6.9 keeps the authorized replacement, startup checks, lifecycle hooks, routes and normal startup recovery in a separate supervised worker on Linux with systemd. After an agent restart, it waits for that original worker and delivers its verified final result without executing the deployment again. Missing or invalid receipts, worker loss or timeout, old unsupervised jobs, data ownership changes and onion provisioning still require support. Preserve the private operation journal and update explicitly after current operations finish. See [supervised replacement](https://docs.imprezahost.com/deployment-progress.html#supervised-replacement).

## API transport protection

Agent 0.6.10 refuses HTTP redirects for API requests, including bootstrap, polling and heartbeat requests carrying agent credentials. Configure the final API URL directly. Existing servers receive this protection after an explicit agent update; installing a newer SDK on another machine does not update the agent executable. Update after active deployment operations finish, then confirm version 0.6.10 after the next heartbeat.

## Controlled builds

Agent 0.6.12 adds an optional owned build executor on Ubuntu 24.04 amd64 with
systemd, AppArmor, local Docker, Buildx and a Compose version supporting an
explicit builder. After upgrading the agent, an administrator can run:

```sh
sudo impreza-agent builder prepare
sudo impreza-agent builder status
```

Preparation verifies a pinned archive checksum and immutable image identity
before enabling the mode for future builds. Existing work and applications
are unchanged. Disable it for future builds with `sudo impreza-agent builder disable`.
Other platforms retain checkpoint cancellation.

With this mode enabled, cancellation from the portal or MCP can stop the owned
build executor before application replacement. The agent confirms cancellation
only after verified cleanup and configuration restoration. Recovery after agent
or host interruption requires matching private identity evidence and authenticated
operation state; missing or inconsistent evidence remains blocked for support.
Deployment work is never replayed automatically.

The rootless executor has bounded CPU, memory and PIDs and no host Docker socket
or bind mount. Its required container-local security exceptions do not provide
a hostile-code sandbox or build-network egress filtering. Review project code
before supplying build credentials. Build cache is disposable between jobs.

See [controlled build setup and limits](https://docs.imprezahost.com/deployment-cancellation.html#controlled-builds).

Agent 0.6.13 adds reviewed PostgreSQL application connections with a separate
stable database owner and dedicated login. Removal verifies the replacement,
disables the login and retains database data. Durable verified results survive
agent/server restarts; incomplete replacement still requires support review.
Credential rotation is not included. See the [connection guide](https://docs.imprezahost.com/service-bindings.html).

## Required health during credential rotation

Agent 0.6.15 requires a Docker healthcheck reporting healthy before PostgreSQL
credential rotation or abandonment can disable an unused login. Missing or optional
startup policies are refused; create a fresh review with the updated API. Health
assurance depends on the application healthcheck. Update explicitly after active
operations finish. See the [connection guide](https://docs.imprezahost.com/service-bindings.html).

## Reviewed routing and data workflows

Agent 0.6.16 adds reviewed traffic switches, password-protected previews, PostgreSQL backup verification and assisted restoration into a new database. The IPv4 Docker egress baseline covers standard bridges only; it is not a complete network sandbox. Existing servers update explicitly with the command above after active deployments finish. See the [deployment safety guide](https://docs.imprezahost.com/deployment-safety.html).

## Release metadata validation

The updater accepts a single numeric version and a single SHA-256 value with LF
or CRLF line endings. Empty, multiline or malformed metadata is rejected before
replacing the installed agent. Release metadata in this repository uses LF.

Before publishing, run `python3 -m unittest discover -s tests` on Linux and test
both `--check` and `--apply` without `IMPREZA_AGENT_VERSION` on a disposable server.
The final verification must use the published updater and automatic stable-version
discovery, in addition to checking the downloaded executable.

## Application metrics and MariaDB connections

Agent 0.6.17 reports per-app resource metrics and supports reviewed MariaDB
connection creation, removal and credential rotation. Update explicitly after
active operations finish. See [application operations](https://docs.imprezahost.com/customer-workflows.html).

## Database recovery isolation

Agent 0.6.18 supports reviewed PostgreSQL restoration to an eligible binding on
another host and verified backup plus assisted restore for managed MariaDB
InnoDB tables. Verification and restore use an operation-specific database
login, which is removed after successful completion. Unsupported MariaDB
objects are refused instead of producing an incomplete backup. Update explicitly
after active operations finish. See [database recovery](https://docs.imprezahost.com/customer-workflows.html#restore).

## Onion service controls

Agent 0.6.19 adds onion service profiles, client authorization and reviewed identity
import, export and rotation. The Tor sidecar uses a pinned multi-architecture image.
Onion service reconciliation can briefly interrupt onion access while Tor restarts;
application containers keep running. Update explicitly after active operations finish.
See [onion services](https://docs.imprezahost.com/onion-services.html).
