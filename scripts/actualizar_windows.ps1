param(
    [switch]$SoloServidor,
    [string]$DesdeCrudo
)

$ErrorActionPreference = 'Stop'
$runtime = Join-Path $env:LOCALAPPDATA 'compras-publicas-ecuador'
$cluster = Join-Path $runtime 'cluster'
$pgctl = Join-Path $runtime 'postgres-18.7\pgsql\bin\pg_ctl.exe'
$python = Join-Path $runtime 'python\Scripts\python.exe'

& $pgctl -D $cluster status | Out-Null
if ($LASTEXITCODE -eq 3) {
    & $pgctl -D $cluster -l (Join-Path $runtime 'postgres.log') -w -t 30 start
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($SoloServidor) { return }

$env:PGHOST = '127.0.0.1'
$env:PGPORT = '55432'
$env:PGDATABASE = 'compras_publicas'
$env:PGUSER = 'compras_pipeline'
$env:PGPASSFILE = Join-Path $runtime 'pgpass.conf'

$argumentos = @('-B', '-m', 'scripts.cargar_postgres')
if ($DesdeCrudo) {
    $argumentos += @('--desde-crudo', (Resolve-Path -LiteralPath $DesdeCrudo).Path)
}

Push-Location (Join-Path $PSScriptRoot '..')
try {
    $ErrorActionPreference = 'Continue'
    & $python @argumentos 2>&1 | Tee-Object -FilePath (Join-Path $runtime 'actualizacion.log')
    $codigo = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $codigo
