# Agent 0.6.41

- Adds an optional, local-only setting for encrypted-root reporting, used by the encrypted-root template tools. It is off by default, only a local root user can change it, the control plane cannot turn it on, and updating the agent does not turn it on.
- Includes code for features that are not released yet. It stays inactive: nothing changes on your server until a feature is released and you turn it on.
- Built with Go 1.26.10, like 0.6.40. Dependencies are unchanged.
