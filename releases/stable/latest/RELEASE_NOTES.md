# Agent 0.6.34

- On IPv6, a forwarded connection rewritten to a unique-local address outside the host is dropped, as the metadata range already is on IPv4. A rewritten connection onto a container address on one of Docker's own bridges is unchanged, and DNS to a unique-local resolver still works.
- While the control plane marks this agent for uptime checks, it does not poll for commands or send heartbeats and application metrics. The uptime target exchange continues. When the mark is removed, polling and reporting resume.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
