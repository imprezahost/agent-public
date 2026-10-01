# Agent 0.6.25

- Application containers can reach the host services your server's firewall allows. Agents 0.6.21 to 0.6.24 blocked every new connection from an application container to the host itself, regardless of the host firewall. From 0.6.25 a port your firewall (for example UFW or firewalld) allows on the host is reachable from your containers, and so are your applications' published ports; other host services stay closed to containers, and the cloud metadata endpoint stays blocked. If you rely on the old behavior, keep the port closed in your host firewall.
- Restoring an application's files stops the application first. The restore stages and verifies the archive while the application keeps running, stops it only for the exchange of its data, and starts the same containers again. If the exchange fails, the previous data is put back, and an agent restart resumes the operation from where it stopped.
- An application stays stopped while a restore job may still be writing to it, including when the agent recovers an interrupted restore. A job that cannot be confirmed stopped holds the operation for review instead of starting the application on files that may still be changing.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
