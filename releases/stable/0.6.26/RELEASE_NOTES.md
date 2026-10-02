# Agent 0.6.26

- A refused or interrupted operation now gets an answer. When the agent is interrupted during an operation and will not repeat it, the server receives a readable failed result instead of a command that stays pending: a verified preparation says what was restored, and anything that cannot be verified says so and asks for an explicit retry. A supervised worker that stopped without a receipt no longer blocks later commands for the same server.
- A network failure while delivering a result no longer marks the application for recovery review. The agent resends with a status the server already understands, and a command the server already closed is accepted instead of being re-sent.
- Every update now installs or repairs the agent's network boot unit, which restores the agent's host rules before Docker starts. If enabling it fails, update.sh says so, names the repair command (systemctl enable impreza-agent-ingress.service) and exits with status 3; the new agent stays installed and running, and the agent retries the enable once at startup. Automation that runs update.sh should treat status 3 as "updated, follow the printed repair step".

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
