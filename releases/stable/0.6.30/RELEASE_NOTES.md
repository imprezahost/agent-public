# Agent 0.6.30

- Zero-downtime redeploys no longer reload the proxy. The routing fragment carries both the serving container and the standby slot with an active health check; a swap is container lifecycle only — the new version is made and proven before the old one stops, and the proxy configuration never changes mid-swap. This removes the request that every reload-with-change used to drop. The health check polls each upstream's readiness path twice a second; expect that traffic in the app's access logs.
- A git redeploy replaces the build context with two directory renames instead of deleting the old tree first; a failure between the renames restores the previous context.
- The installer's binary download rides the same verified fetch as the manifest: https-only for network origins (no downgrade through redirects), plain file copies for distributor-local trees, and the updater's 180-second ceiling on slow links. A fresh install also ships the ingress boot unit, enabled.
- The daemon and the CLI serialize egress firewall applies on the same host through a lock file in the agent's state directory.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
