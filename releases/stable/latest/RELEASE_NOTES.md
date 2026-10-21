# Agent 0.6.35

- A deployment result now says whether the existing public HTTPS check confirmed the application's address, and warns when the public route could not be applied. The application stays installed either way; the result is one observation at deployment time, not continuous monitoring.
- The updater checks the offered agent's size, digest and embedded version before it touches the installed ingress boot unit. A refused update leaves the installed agent and its boot unit unchanged.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
