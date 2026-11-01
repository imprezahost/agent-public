# Agent 0.6.44

Released 2026-11-01. Changes below are relative to stable 0.6.43.

- Network and cryptography dependencies are updated: golang.org/x/net 0.62.0, golang.org/x/crypto 0.58.0 and golang.org/x/sys 0.49.0.
- Failover standby: after a verified checkpoint apply, the standby application stays stopped until the server promotes it. The checkpoint announcement format is unchanged.
- Domain alias: the agent can serve the `www` alias of a custom domain when the server enables it for that deployment. The server checks the domain's DNS before enabling it; the agent never adds an alias on its own.
- Registry mirror: the agent can pull images through a registry mirror when the server's policy for that host names one. Without that policy, image pulls are unchanged.
- Built with Go 1.26.10 for Linux amd64 and arm64. Two local builds of each architecture produced identical binaries; this is not an independent build by another organization.
- Updates remain an explicit customer action and preserve the agent's identity, configuration and application containers. Finish active operations before updating.
