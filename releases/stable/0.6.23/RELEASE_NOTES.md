# Agent 0.6.23

- Large image pulls no longer fail at a fixed five-minute limit. A pull keeps extending its budget while it downloads, up to 45 minutes; a pull that stalls for ten minutes or reaches that limit fails as a retryable error. Deployments with an onion address or a data directory use the same supervised pull.
- A build that runs past its ten-minute budget, or a pull or build whose worker stops without a result, now ends the deployment as a retryable failure and restores the previous configuration. Before, such a build could stop the agent from running any later command on that server, including uninstalls and updates.
- If the server already closed a deployment the agent was still recovering, the agent restores and verifies the previous configuration, then moves on to the next command instead of waiting for manual reconciliation.
- Deployment variables are written to the application's `.env` file literally: `$`, `${...}`, quotes, backslashes and ` #` reach the container unchanged, and a value can no longer define or change another variable. If a value relied on another variable expanding inside it, set the final value directly.
- A one-shot service that another service waits on to complete successfully, such as certificate setup, no longer marks the application degraded. A long-running service that stops still does.
- Removing an application no longer fails on a server that never ran Tor. An onion deployment that fails after its address was created no longer leaves the onion service configured, and an invalid directory in the onion configuration is set aside instead of stopping Tor for every onion application on the server.
- On servers with controlled builds enabled, deployments with an onion address or a data directory now build under the controlled builder too.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
