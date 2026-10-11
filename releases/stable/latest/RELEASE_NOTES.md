# Agent 0.6.31

- A domain change waits for one certificate-authority retry before giving up: the new domain's HTTPS check runs for up to three minutes (retry delay, issuance time and a margin) instead of failing on a first attempt made while the new DNS record was still propagating. If the certificate still is not ready, the previous domain keeps serving and the error says that the new domain's certificate did not become ready in time.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
