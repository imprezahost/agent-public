# Agent 0.6.29

- The installer works again on a box without Docker: a fresh install no longer dies with "invalid pinned version" after installing Docker (the OS release data was overwriting the requested agent version inside the installer).
- The updater is stricter about the health of a new version before committing to it: the post-update watch runs thirty seconds and treats any restart of the agent service as a failure, so a candidate binary that crashes after the old ten-second window — or starts crash-looping at any point inside it — is rolled back to the previous version instead of being adopted and left looping. A candidate that first dies after the thirty-second window is still adopted; that limit remains.
- Concurrent reapplications of the network egress baseline — the periodic reconcile, the firewalld reload and the deployment path that creates or reuses the proxy network — are serialized inside the agent. None of them can tear down the iptables rules another apply just installed, so a deployment no longer races the reconcile into a window where a Docker bridge has no egress drops.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
