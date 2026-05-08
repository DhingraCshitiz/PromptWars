param(
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $NoBuild) {
    docker compose up --build api
} else {
    docker compose up api
}
