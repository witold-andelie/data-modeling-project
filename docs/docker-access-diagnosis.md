# Docker access diagnosis — 2026-10-16

Read-only investigation requested by the user. No Docker/WSL restart, process
termination, container mutation, ACL edit or token change was performed.

## Finding

The current command process runs under a restricted Windows token. Its
restricted identity set is not granted access by the Docker Engine pipe DACL.
This explains why the CLI cannot open the engine connection even though the
normal user belongs to docker-users.

## Evidence

- `docker context show`: desktop-linux.
- Its configured endpoint is `npipe:////./pipe/dockerDesktopLinuxEngine`.
- `docker version` repeatedly prints client version 29.7.2, followed by
  permission denied for that pipe; no server response is obtained.
- Current user is Administrator; docker-users membership is enabled.
- Windows token queries: IsTokenRestricted=true, TokenHasRestrictions=1,
  TokenElevationType=3 (limited), TokenElevation=0, TokenIsAppContainer=0.
- TokenRestrictedSids contains four entries: two additional restricting SIDs,
  the session logon SID and Everyone. None appears in the engine pipe allow ACEs.
- Reading pipe security information succeeded. Its protected DACL grants
  Administrators and SYSTEM full access, and the Administrator user and
  docker-users group mask 0x12019f. The descriptor was only read.
- Docker host and VM logs show other clients successfully exchanging container
  stats requests at approximately 2026-10-16 17:56 UTC. This supports that the
  engine is serving other clients, rather than globally unavailable.

Microsoft documents the additional SID access check for restricted tokens:
https://learn.microsoft.com/en-us/windows/win32/secauthz/restricted-tokens

Docker documents named-pipe access controls on Windows:
https://docs.docker.com/desktop/setup/install/windows-permission-requirements/

## Operational consequence

This is an execution-permission boundary, not a database project code problem.
No restart or further docker-users membership change is indicated by these
observations. Access must be authorized through the execution environment's
supported permission mechanism; do not weaken the pipe ACL, enable an unauthenticated
TCP endpoint or route around the denied connection. During the original diagnosis,
an approved elevation path was not available; Compose settings alone were not
evidence of actual container limits.

## Later authorized execution — 2026-10-16

The supported approval mechanism subsequently became available. One approved
read-only check returned Docker client/engine 29.7.2 and Desktop 4.89.0. Both
project containers were exited and had HostConfig.Memory=0. The ordinary
restricted startup path still failed at the engine pipe; an approved invocation
of `scripts/start-database.ps1 -Service mysql` then succeeded. This does not mean
the restricted token or pipe ACL was changed.

The previously exited MySQL container was recreated by Compose using the existing
volume and became healthy. Docker inspect verified Memory=536870912 and
MemorySwap=536870912 bytes. Full loading and MySQL verification completed within
that limit. Image identity and inspected settings are archived in
`artifacts/runtime/mysql.json`. Neo4j has not been started in this continuation;
its actual 1GiB limit is still unverified. No running container was stopped or
recreated, and no Docker/WSL restart or process termination was performed during
that first continuation.

## Authorized single-engine completion — 2026-10-16

The user subsequently authorized graceful stopping of databases started for this
task and corrected the overly broad lifecycle restriction in AGENTS.md. MySQL's
full process list showed no other user sessions. It was stopped gracefully with
`docker stop --timeout -1`, preserving its volume. The startup script then
recreated the already-exited Neo4j container with Memory=1073741824 and
MemorySwap=1073741824 bytes and verified its health. Full import, business queries,
audits and negative cases completed within that hard limit.

After verification, Neo4j SHOW TRANSACTIONS found no other active transactions;
the task-owned container was also stopped with an indefinite graceful timeout.
Final inspect shows both project containers exited with exit code 0 and
OOMKilled=false; their 512MiB/1GiB limits remain set. Evidence is in
`artifacts/runtime/mysql.json`, `neo4j.json` and `final-containers.json`.
No volume was deleted. Docker Desktop, WSL and unrelated containers/processes
were not restarted, shut down or terminated.
