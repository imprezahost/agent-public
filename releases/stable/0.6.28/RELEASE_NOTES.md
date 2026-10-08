# Agent 0.6.28

- Readiness is measured on the clock: a service without a Docker healthcheck counts as ready only after a full readiness window has passed since its last restart, and a sidecar that keeps restarting next to a healthy service is no longer reported ready.
- A failed git clone no longer takes down the running application: the new source is cloned into a staging directory and replaces the previous one only after the clone and the pinned-commit checkout both succeed.
- Every Docker network the agent creates (the shared proxy network and each deployment's own) gets the egress rules immediately; if they cannot be applied, the deploy fails instead of leaving the new network without them.
- A deployment whose compose.yaml is missing uninstalls and rolls back cleanly, and log requests explain that there are no containers instead of returning an error.
- Responses read from the control plane are size-capped, so a misbehaving endpoint cannot exhaust the agent's memory.
- Agent-side support for pull-request previews, the host inventory, public status pages served on the app's onion address and uptime probing across larger target lists. These follow the platform's own rollout.
- The installer (install.sh) now verifies the channel's signed release manifest before downloading, resolves the version through it and no longer pipes a remote script into a shell to install Docker.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
