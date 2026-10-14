# Agent 0.6.33

- Uninstall no longer reports success until the agent has confirmed that the application's containers are gone, including those of a legacy Compose project name. If a container survives, the uninstall fails and keeps the application's configuration so it can be retried.
- The first proxy reload after the agent starts waits until the local proxy admin is ready, instead of failing while that admin is still starting.
- A full queue of accepted backup cleanups no longer holds the next command. The agent warns only after the control plane has accepted the result.
- After a database promotion, the agent drops a transit schema only when it is empty and belongs to the same owner.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents 0.6.22 and later can update from the portal, API or MCP; older agents update once with update.sh.
See https://docs.imprezahost.com/agent-updates.html.
