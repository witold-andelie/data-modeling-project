# Project instructions

## User scope

Build the database coursework first. Data mining belongs to a separate course;
retain versioned export/result-validation contracts only. Defer report cover
metadata and report prose until requested.

## Memory policy

The user reported high host memory usage and requested bounded Docker memory.

- Other terminals are doing work on this computer. Do not interrupt them:
  do not restart Docker Desktop, shut down WSL, kill processes, or stop/recreate
  unrelated containers or project containers being used by another terminal.
- The user authorizes normal lifecycle management of this task's project databases:
  after a database's loading/verification has finished, check for other active work,
  then stop it gracefully to switch to the other project database. Do not delete
  volumes. No repeated confirmation is needed for this authorized single-database
  workflow. At the end, stop databases started solely for this task to release RAM.
- Use `scripts/start-database.ps1 -Service mysql` or `-Service neo4j` to run one
  project database at a time. The script refuses to switch while the other
  database is running and inspects existing running containers without recreating them.
- Keep the Compose memory limits: MySQL 512 MiB; Neo4j 1 GiB. They apply when
  containers are created/recreated, not merely when the YAML is edited.
- Avoid simultaneous database loading/queries, full-data Python jobs and UML
  rendering. Use smaller batches if an operation exceeds its memory budget.
- Check Docker access and actual container limits before claiming enforcement.
  The ordinary restricted Windows token may be denied access to the engine pipe;
  use the supported approval mechanism if a necessary call is blocked. Approved
  executions have succeeded. Diagnosis and evidence are in
  `docs/docker-access-diagnosis.md`. Avoid repeatedly retrying denied calls under
  unchanged permissions; do not weaken pipe ACLs or bypass the permission boundary.
- Container limits do not cap Docker Desktop UI, WSL VM or unrelated containers.
  The inspected user `.wslconfig` allowed 6 GB; it has not been modified here.
- Do not shut down all WSL distributions or delete Docker volumes to reclaim RAM.
