$ErrorActionPreference = 'Stop'
$nombre = 'Compras publicas Ecuador - actualizar datos'
$archivo = Join-Path $PSScriptRoot 'actualizar_windows.ps1'
$raiz = Split-Path -Parent $PSScriptRoot
$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$argumentos = '-NoProfile -NonInteractive -WindowStyle Hidden -File "{0}"' -f $archivo

$existente = Get-ScheduledTask -TaskName $nombre -TaskPath '\' -ErrorAction SilentlyContinue
if ($existente) {
    if ($existente.Actions.Arguments -ne $argumentos) {
        throw 'Ya existe una tarea con el mismo nombre y una acción distinta.'
    }
    $existente
    return
}

$accion = New-ScheduledTaskAction -Execute $powershell -Argument $argumentos -WorkingDirectory $raiz
$calendario = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At '08:00'
$usuario = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $usuario -LogonType Interactive -RunLevel Limited
$opciones = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew `
    -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 15) -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName $nombre -Action $accion -Trigger $calendario -Principal $principal -Settings $opciones
