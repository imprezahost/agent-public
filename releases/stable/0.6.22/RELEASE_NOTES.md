# Agent 0.6.22

- Changes an application's domain through a verified handover: the previous hostname keeps serving until the new route passes a pinned TLS check, and a failed check restores the previous route. Agents before 0.6.22 are refused before anything changes.
- Applies agent updates requested from the portal, API or MCP, installing only the exact version named by the signed channel manifest and restoring the previous executable if the new one does not start.
- Runs the Impreza Shield proxy image (Caddy 2.11.4 with the Coraza WAF, a proof-of-work gate and rate limiting), pinned by digest. New deployments start on the standard profile, which audits and never blocks; existing deployments keep Shield off until changed. Servers with onion services move the shared proxy to the new image when the updated agent starts; other servers move at their next deployment. Certificates are kept.
- Reports per-application proxy request counters with the metrics, without visitor identity.
- Supports the confined, time-limited sandbox runtime class.
- No longer reports a failure after removing the temporary containers of backups, restores, tasks, file reads and CLI runs.

From this release the stable channel publishes a signed manifest, and update.sh verifies it before downloading. Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating. Agents before 0.6.22 update once with update.sh; later updates can also be requested from the portal, API or MCP.
See https://docs.imprezahost.com/agent-updates.html.
