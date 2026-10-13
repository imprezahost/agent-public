# Agent 0.6.32

- Bind mounts under an application's `./data` are created by the agent, component by component and refusing symbolic links, before the data directory owner is applied. An image that runs as a non-root user can write its own state on the first start, and the ownership pass no longer follows a link that a container planted under `./data`.
- A restore journal the agent cannot verify keeps its application quarantined for more operations: onion address rotation and removal, failover receipt and traffic switches that target it are refused until support reconciles the journal. Health checks, logs and moving traffic away from the application keep working.
- Restores are steadier across agent restarts: the waiting deadlines are recorded before each wait, so a restart resumes the remaining time instead of starting a new one, and a restore job that disappears mid-exchange is stopped and reported, with the application brought back when nothing was changed.
- Old copies of a release no longer keep a service-binding password after it was rotated or removed.
- The working folder of a finished app backup is removed once the result is acknowledged by the control plane, so it no longer stays on the server's disk.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
