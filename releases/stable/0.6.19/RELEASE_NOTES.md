# Agent 0.6.19

Adds onion service profiles, client authorization and reviewed identity import,
export and rotation, with a pinned Tor image for Linux amd64 and arm64.

Onion service reconciliation preserves existing identities and can briefly interrupt
onion access while Tor restarts. Application containers keep running.

Update explicitly after active operations finish. The updater preserves agent
identity, configuration and application data, and restores the previous executable
if the new service fails to start.

See [onion services](https://docs.imprezahost.com/onion-services.html).
