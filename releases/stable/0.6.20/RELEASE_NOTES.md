# Agent 0.6.20

- Private onion previews install reviewer authorization before first publication.
- Repeated deploys preserve reviewer revocations; HTTP/HTTPS onion Git sources use Tor without direct fallback.
- Confirmed purge removes managed retained identity copies and protects active identities. External exports and backups remain.
- Custom applications can opt into isolated Tor runtime egress with Docker Engine 28+ and SOCKS-aware libraries.
- IPv6 forwarding policy complements the IPv4 baseline; host networking and alternative drivers remain outside it.
- Source builds report bounded local findings using signed vulnerability advisories. Missing or partial data is not a clean security assessment.

Updates are explicit customer actions and preserve agent identity, configuration and applications. Finish active operations before updating.
See https://docs.imprezahost.com/agent-updates.html and https://docs.imprezahost.com/onion-services.html.
