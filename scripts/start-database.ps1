param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('mysql', 'neo4j')]
    [string]$Service
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    & docker info --format '{{.ServerVersion}}'
    if ($LASTEXITCODE -ne 0) {
        throw 'Cannot access Docker Engine. No database was started. Check Docker Desktop and Docker CLI access.'
    }
    & docker compose config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Invalid Compose configuration.' }
    $otherService = if ($Service -eq 'mysql') { 'neo4j' } else { 'mysql' }
    $runningServices = @(& docker compose ps --status running --services)
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect running services; no startup attempted.' }
    if ($runningServices -contains $otherService) {
        throw "$otherService is already running. Leave it available to other terminals; finish its work before switching databases."
    }
    if ($runningServices -notcontains $Service) {
        # Existing running containers are never restarted/recreated by this script.
        & docker compose up -d --wait --no-deps $Service
        if ($LASTEXITCODE -ne 0) { throw "Startup failed: $Service" }
    }
    $containerIds = @(& docker compose ps -q $Service)
    if ($LASTEXITCODE -ne 0 -or $containerIds.Count -ne 1) {
        throw 'Expected exactly one running database container.'
    }
    $configuredMemory = & docker inspect --format '{{.HostConfig.Memory}}' $containerIds[0]
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the memory limit.' }
    $expectedMemory = if ($Service -eq 'mysql') { 536870912L } else { 1073741824L }
    if ([long]$configuredMemory -ne $expectedMemory) {
        throw 'The existing container has a different memory limit. It was left running; schedule recreation after its current work finishes.'
    }
    $configuredSwap = & docker inspect --format '{{.HostConfig.MemorySwap}}' $containerIds[0]
    if ($LASTEXITCODE -ne 0 -or [long]$configuredSwap -ne $expectedMemory) {
        throw 'The container has a different memory+swap limit. It was left running.'
    }
    & docker inspect --format 'Memory limit: {{.HostConfig.Memory}} bytes; memory+swap: {{.HostConfig.MemorySwap}} bytes' $containerIds[0]
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect the configured memory limit.' }
    & docker stats --no-stream $containerIds[0]
    if ($LASTEXITCODE -ne 0) { throw 'Could not read runtime memory usage.' }
    $containerInfo = @(& docker inspect $containerIds[0] | ConvertFrom-Json)[0]
    if ($LASTEXITCODE -ne 0) { throw 'Could not capture container evidence.' }
    $imageInfo = @(& docker image inspect $containerInfo.Image | ConvertFrom-Json)[0]
    if ($LASTEXITCODE -ne 0) { throw 'Could not capture image identity.' }
    $evidence = [ordered]@{
        checked_at = [DateTime]::UtcNow.ToString('o')
        service = $Service
        container_id = $containerInfo.Id
        container_name = $containerInfo.Name
        status = $containerInfo.State.Status
        oom_killed = $containerInfo.State.OOMKilled
        image = $containerInfo.Config.Image
        image_id = $containerInfo.Image
        image_digests = @($imageInfo.RepoDigests)
        memory_bytes = $containerInfo.HostConfig.Memory
        memory_swap_bytes = $containerInfo.HostConfig.MemorySwap
        memory_reservation_bytes = $containerInfo.HostConfig.MemoryReservation
        expected_memory_bytes = $expectedMemory
        limits_match = $true
    }
    $evidenceDir = Join-Path $projectRoot 'artifacts/runtime'
    New-Item -ItemType Directory -Path $evidenceDir -Force | Out-Null
    $evidence | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $evidenceDir "$Service.json")
} finally {
    Pop-Location
}
