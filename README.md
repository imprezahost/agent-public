# imprezahost/agent-public

Public distribution of the Impreza Platform agent. This project is
**intentionally public** so customer VPSes can fetch the installer
and binaries without any credentials.

Hosted on GitHub (`github.com/imprezahost/agent-public`) because the
self-hosted GitLab at `git.imprezahost.com` has an org policy that
disables per-project public visibility. The internal source of truth
remains GitLab (`git.imprezahost.com/impreza/agent-public`) — GitHub
is the customer-facing mirror.

If you're an Impreza Host customer, you don't need to clone or read
this repo — the install one-liner ships from the My Apps panel.

If you're an operator updating the agent: see "Cutting a release"
below.

## What lives here

| Path | Purpose |
|------|---------|
| `install.sh` | curl-pipe installer script. Detects OS/arch, installs Docker if missing, downloads the agent binary, installs the systemd unit, registers the agent with the control plane. |
| `releases/stable/latest/impreza-agent-linux-amd64` | Static Go binary (`go build -trimpath -ldflags="-s -w"`), Linux amd64. |
| `releases/stable/latest/impreza-agent-linux-arm64` | Same, Linux arm64. |

The Caddy sidecar image (`ghcr.io/imprezahost/caddy:2-cf`) lives in
GitHub Container Registry, built by the `caddy-image.yml` workflow in
`imprezahost/impreza-devkit` — see "Caddy sidecar image" below.

URLs the agent + install.sh consume:

```
https://raw.githubusercontent.com/imprezahost/agent-public/main/install.sh
https://raw.githubusercontent.com/imprezahost/agent-public/main/releases/stable/latest/impreza-agent-linux-amd64
docker pull ghcr.io/imprezahost/caddy:2-cf
```

## Customer install (informational — runs automatically post-VPS-provision)

```sh
curl -fsSL \
  https://raw.githubusercontent.com/imprezahost/agent-public/main/install.sh \
  | IMPREZA_BOOTSTRAP=bst_xxxxxxxxxxxxxxxx sh
```

The bootstrap token is single-use, expires in 10 min, and is minted
by the Impreza Platform when a customer either (a) buys a VPS with
an app pre-selected at the cart, or (b) clicks "Install Impreza
Agent" in their clientarea.

## Cutting a release

### Agent binary

From `impreza-devkit/agent-go` on any host with Go ≥ 1.22:

```sh
cd impreza-devkit/agent-go

GOOS=linux GOARCH=amd64 CGO_ENABLED=0 \
  go build -trimpath -ldflags="-s -w -X main.version=vX.Y.Z" \
  -o /tmp/impreza-agent-linux-amd64 .

GOOS=linux GOARCH=arm64 CGO_ENABLED=0 \
  go build -trimpath -ldflags="-s -w -X main.version=vX.Y.Z" \
  -o /tmp/impreza-agent-linux-arm64 .

# Sanity:
file /tmp/impreza-agent-linux-*
#   ELF 64-bit LSB executable, x86-64, statically linked
#   ELF 64-bit LSB executable, ARM aarch64, statically linked

# Commit:
cp /tmp/impreza-agent-linux-* releases/stable/latest/
git add releases/stable/latest/
git commit -m "Bump impreza-agent to vX.Y.Z"
git push
```

### install.sh

Source is also kept in
`imprezaapi/whmcs/modules/addons/imprezaapi/dist/install.sh` for
historical reasons (the WHMCS module used to host it under
Apache). When changing the script, edit both copies until that
mirror is retired.

### Caddy sidecar image

Built + pushed by the GitHub Actions workflow
`.github/workflows/caddy-image.yml` in `imprezahost/impreza-devkit`.
Two trigger paths:

  - **Tag push** (preferred for new Caddy versions):
    ```sh
    git -C impreza-devkit tag caddy-v2.10.0
    git -C impreza-devkit push origin caddy-v2.10.0
    ```
    Builds multi-arch (linux/amd64 + linux/arm64) and pushes three
    tags: `:<X.Y.Z>-cf`, `:2-cf`, `:latest-cf` — all to
    `ghcr.io/imprezahost/caddy`. The agent's `caddy.go` pins to
    `:2-cf`, so a new release auto-rolls out to fresh agent installs.

  - **Manual** (for base-image security re-builds with no source
    change): open the workflow in GitHub Actions UI → "Run workflow"
    → enter the version → submit.

For a local smoke build (no push):

```sh
cd impreza-devkit
docker build \
  --build-arg CADDY_VERSION=2 \
  -t ghcr.io/imprezahost/caddy:2-cf \
  -f agent-go/packaging/caddy/Dockerfile \
  .
```

## Architecture trade-offs

  - **Why public**: avoids shipping any credentials to customer
    VPSes. The agent binary + Caddy image are not secrets — the
    bootstrap token (single-use, 10-min TTL) is what authorises a
    specific VPS to talk to the control plane.
  - **Why GitHub raw URLs and not a separate CDN**: zero extra
    infra. GitHub handles the bandwidth + caching. When traffic
    pattern outgrows raw-file serve, we add a CDN in front
    transparently.
  - **Why GitHub and not the self-hosted GitLab**: an org policy on
    `git.imprezahost.com` disables per-project public visibility,
    so a GitLab raw URL would have stayed credential-gated for
    customer VPSes. GitHub is the mirror; GitLab remains the
    primary internal repo.
  - **Why `main` branch and not Releases / tags**: at our cadence
    (occasional, operator-triggered) the branch-tracking approach
    is simpler. Promoting to tags is a one-line `git tag` away
    when we want immutable URLs.
