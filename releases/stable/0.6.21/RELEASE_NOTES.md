# Agent 0.6.21

- Runs Tor image 1.0.1. An upgraded tor package resets the owner of the Tor data directory, and the daemon refused to start after it; the new image restores the owner on every start, so onion services start again.
- Servers with onion services move Tor to the new image when the updated agent starts; other servers move at their first onion deployment.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating.
See https://docs.imprezahost.com/agent-updates.html and https://docs.imprezahost.com/onion-services.html.
