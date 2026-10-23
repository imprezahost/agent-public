# Agent 0.6.37

- An onion address is reported ready only after Tor confirms that it published the service, instead of probing the address from outside.
- A staging clone of an app that runs as a fixed user, such as Memos, keeps that user and gets no extra capabilities.
- Includes code for maintenance features that are not released yet. It stays inactive: nothing changes on your server until a feature is released and you turn it on.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
