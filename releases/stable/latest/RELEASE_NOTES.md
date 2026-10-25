# Agent 0.6.39

- Built with Go 1.26.10. This picks up security fixes in the Go standard library that the agent uses for its connection to Impreza: TLS certificate verification, HTTP/1 and HTTP/2 handling, and MIME header parsing.
- Changing an app's domain now reloads the proxy before the switch is recorded as finished, so the old domain stops being served even if the agent restarts in the middle of the change.
- Includes code for maintenance features that are not released yet. It stays inactive: nothing changes on your server until a feature is released and you turn it on.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
