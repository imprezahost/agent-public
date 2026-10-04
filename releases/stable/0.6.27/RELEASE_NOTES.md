# Agent 0.6.27

- Shield v2: the managed proxy now runs the web application firewall with an IP allowlist, an under-attack mode, per-path proof-of-work challenges and per-window request counters, configured per route from the portal, API or MCP. The first route change after the update recreates the proxy container on the new image; its certificates and data are kept. Routes without a Shield configuration are untouched.
- Ready swap on redeploy: when you opt in, the new release is started and its readiness is checked before traffic moves to it, and the previous release keeps serving until then.
- Groundwork with no change in behaviour until the platform enables it: an uptime probe capability, and running a file restore with the application stopped.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
