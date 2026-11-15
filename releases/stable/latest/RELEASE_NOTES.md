# Agent 0.6.45

Released 2026-11-15. Changes below are relative to stable 0.6.44.

- Private registry images. Image-mode deployments can pull from a private registry. The agent announces `registry-auth-v1`; a job carries only a `registry_auth` flag, and the agent fetches the deployment's credential just in time with the job's own control token. The credential exists only in a private Docker configuration for that job's pull (a `0700` directory with a `0600` file) and is wiped after the pull, on success and on failure. Registry output is withheld; a refusal reports `REGISTRY_AUTH_DENIED`. It works with the control plane that is already live; agents older than 0.6.45 are refused by the server instead of receiving the credential.
- Credential origin. The agent no longer sends its credentials to an API origin that was not authorized separately, and the authorized origin is passed through to the managed proxy. An agent that is already installed keeps running after the update, unless its control plane URL uses plain http:// on a host that is not .onion or loopback: that agent stops sending its credential and needs a new bootstrap with https.
- Preview proxy. The managed proxy's preview configuration stays valid when no origin is bound.
- Registry mirror. The mirror is announced as `registry-mirror-v2`. The agent creates its own registry client key, stays quiet until the server asks for a certificate request, and only reports the mirror as active after a cold canary and a check of `docker info` and the Docker daemon journal. Every uncertain path fails closed, and undo removes the agent's empty directory so the mirror can be enabled again.
- Privacy. The agent's journal no longer records the customer's onion address, application host, forge URL or the managed proxy's output.
- Encrypted Ubuntu 22.04 templates use the distribution's dropbear-initramfs package for remote unlock.
- Built with Go 1.26.10 for Linux amd64 and arm64. The release binaries were rebuilt independently by a second reviewer and matched bit for bit; the 0.6.44 binaries rebuilt the same way also match the published ones.
- Updates remain an explicit customer action and preserve the agent's identity, configuration and application containers. Downgrades are refused by the updater. Finish active operations before updating.
