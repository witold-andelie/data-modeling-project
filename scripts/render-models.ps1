param([Parameter(Mandatory=$true)][string]$PlantUmlJar)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$jar = (Resolve-Path -LiteralPath $PlantUmlJar).Path
$target = Join-Path $projectRoot 'artifacts/models'
New-Item -ItemType Directory -Path $target -Force | Out-Null
$models = Get-ChildItem -LiteralPath (Join-Path $projectRoot 'models') -Filter '*.puml'
foreach ($model in $models) {
    & java '-Xmx256m' '-Djava.awt.headless=true' -jar $jar -charset UTF-8 -tpng -o $target $model.FullName
    if ($LASTEXITCODE -ne 0) { throw "PlantUML failed: $($model.Name)" }
}
$manifest = [ordered]@{
    rendered_at = [DateTime]::UtcNow.ToString('o')
    jar_sha256 = (Get-FileHash -LiteralPath $jar -Algorithm SHA256).Hash.ToLower()
    java_heap_max = '256m'
    images = @($models | ForEach-Object {
        $png = Join-Path $target ($_.BaseName + '.png')
        if (-not (Test-Path -LiteralPath $png)) { throw "Missing rendered PNG: $png" }
        [ordered]@{source=$_.Name; png=([IO.Path]::GetFileName($png)); bytes=(Get-Item -LiteralPath $png).Length;
            source_sha256=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower()}
    })
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $target 'manifest.json')
Write-Output "Rendered UML PNG files: $target"
