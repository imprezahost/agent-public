# Agent 0.6.36

- Changing an application's domain keeps the current domain serving until the new one is proven. An interrupted change is either finished or undone, so the application is not left without a working address.
- The Tor sidecar runs exactly the Tor version pinned by its image digest.
- A custom build refuses changed inputs before any container starts.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
