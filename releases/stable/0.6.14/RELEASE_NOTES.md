# Agent 0.6.14

Adds reviewed PostgreSQL credential rotation. The control plane reserves a
distinct login revision; the agent replaces the consumer with the rotated
credential and disables the previous login only after the replacement is
verified healthy. A failed startup keeps the serving credential; an
unconfirmed disable stays pending cleanup for a newly reviewed retry; a
pending rotation can be abandoned while no cleanup is outstanding. Database
data is always retained. Rotation outcomes survive agent restarts and host
reboots through the durable journal.

Agents without the rotation capability refuse the dispatch; the rotation is
never forced. After active deployments finish, update explicitly using the
documented update command. Identity, configuration and applications are
preserved. There is no automatic fleet update.

See the [connection guide](https://docs.imprezahost.com/service-bindings.html).
