# Impreza Agent 0.6.48

- Pins the reviewed Caddy image 2.11.9-s2 by digest (sha256:5ad8937cf27f9ae1793e8c2deea88f827903254937f83fa28e10b9b3cfcb7563), whose Impreza DNS provider accepts the authorized origin the agent writes. Apps on managed subdomains get their certificate and public route again.
- The Caddy image is built with golang.org/x/crypto v0.59.0 and golang.org/x/sys v0.50.0 (GO-2026-5932 closed).
- Linux amd64 and arm64 binaries rebuilt reproducibly with Go 1.26.11.
