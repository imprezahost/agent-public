# Agent 0.6.13

Adds reviewed PostgreSQL application connections with a dedicated login and
separate database owner. Credentials are delivered only to the authorized
operation and preserved during route changes. Removal verifies a healthy
replacement, disables the login and retains database data. Verified durable
results can be acknowledged after agent or server restart without replaying
replacement. Missing receipts or incomplete replacement require support review.

Credential rotation is not included. After active deployments finish, update
explicitly using the documented update command. Identity, configuration and
applications are preserved. There is no automatic fleet update.

See the [connection guide](https://docs.imprezahost.com/service-bindings.html).
