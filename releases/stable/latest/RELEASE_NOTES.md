# Agent 0.6.40

- Fixes how the agent reads small system attribute files. Some kernels report a larger size than the content these files actually hold, which made an encrypted-disk check report the wrong result. Reads stay bounded, and oversized values are still refused.
- Includes code for features that are not released yet. It stays inactive: nothing changes on your server until a feature is released and you turn it on.
- Built with Go 1.26.10, like 0.6.39. Dependencies are unchanged.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
