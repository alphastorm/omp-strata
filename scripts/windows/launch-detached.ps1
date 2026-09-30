[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Command,
    [Parameter(Mandatory = $true)][string]$Log,
    [string]$WorkingDirectory = $env:USERPROFILE
)

# Runs one PowerShell command outside the calling SSH session's job object and returns its PID as JSON.
# Windows OpenSSH terminates every descendant of the session on disconnect, including Start-Process
# children; a process created through WMI (Win32_Process.Create) is parented by WmiPrvSE and survives.
# Pattern adopted from alphastorm/omp-ninfer scripts/hosts/launch-detached.ps1. The command text is
# written verbatim into a wrapper script next to the log, so no second layer of quoting applies.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$logDir = Split-Path -Parent $Log
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$wrapper = [IO.Path]::ChangeExtension($Log, '.launch.ps1')
$body = '$ErrorActionPreference = ''Continue''' + "`r`n" + '& { ' + $Command + " } *> '" + $Log.Replace("'", "''") + "'`r`n" + 'exit $LASTEXITCODE' + "`r`n"
[IO.File]::WriteAllText($wrapper, $body, [Text.UTF8Encoding]::new($false))
$line = 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $wrapper + '"'
$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = $line
    CurrentDirectory = $WorkingDirectory
}
if ($result.ReturnValue -ne 0) { throw "Win32_Process.Create returned $($result.ReturnValue)" }
[ordered]@{ pid = $result.ProcessId; log = $Log; wrapper = $wrapper } | ConvertTo-Json -Compress
