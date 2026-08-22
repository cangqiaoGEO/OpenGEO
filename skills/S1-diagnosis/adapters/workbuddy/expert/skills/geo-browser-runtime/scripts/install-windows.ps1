$ErrorActionPreference = "Stop"

$AgentBrowser = Get-Command agent-browser -ErrorAction SilentlyContinue
if (-not $AgentBrowser) {
    $Node = Get-Command node -ErrorAction SilentlyContinue
    $Npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $Node -or -not $Npm) {
        Write-Error "Node.js 18+ and npm are required before GEO browser collection"
    }

    $NodeMajor = [int]((node -p 'process.versions.node.split(".")[0]'))
    if ($NodeMajor -lt 18) {
        Write-Error "Node.js 18+ is required, current version: $(node --version)"
    }

    Write-Host "Installing agent-browser CLI"
    npm install -g agent-browser
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    Write-Host "Installing agent-browser browser runtime"
    agent-browser install
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

agent-browser doctor
exit $LASTEXITCODE
