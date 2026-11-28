# ---------------------------------------------------------------------------
#  HozoorYar server setup. Must run elevated (Administrator).
#   1. fixes the LAN address of the Wi-Fi adapter so the phone always finds it
#   2. opens TCP 8000 in Windows Firewall
#   3. registers a startup task that boots the service with Windows
# ---------------------------------------------------------------------------
param(
    [string]$Ip = '192.168.1.10',
    [string]$IfAlias = 'Ethernet 2',
    [string]$Mask = '255.255.255.0',
    [string]$Gw = '192.168.1.1'
)
$Root = 'C:\Users\HP\Documents\attendance-app'

function Step($t) { Write-Host ""; Write-Host "=== $t ===" -ForegroundColor Cyan }

Step '1/3 static IP'
$iface = Get-NetIPInterface -InterfaceAlias $IfAlias -AddressFamily IPv4
if ($iface.Dhcp -eq 'Enabled') {
    netsh interface ipv4 set address name="$IfAlias" static $Ip $Mask $Gw | Out-Null
    Write-Host "switched $IfAlias from DHCP to static $Ip/$Mask gw $Gw"
} else {
    Write-Host "$IfAlias already static: $Ip"
}
# Router stays the primary DNS; Cloudflare as a fallback.
netsh interface ipv4 set dnsservers name="$IfAlias" static $Gw primary | Out-Null
netsh interface ipv4 add dnsservers name="$IfAlias" 1.1.1.1 index=2 | Out-Null

Step '2/3 firewall'
Get-NetFirewallRule -DisplayName 'HozoorYar API 8000' -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName 'HozoorYar API 8000' -Direction Inbound -Action Allow `
    -Protocol TCP -LocalPort 8000 -Profile Any | Out-Null
Write-Host 'inbound TCP 8000 allowed (all profiles)'

Step '3/3 startup task'
$taskName = 'HozoorYar Server'
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host 'removed previous task'
}
$action = New-ScheduledTaskAction -Execute "$Root\scripts\run_server.cmd" -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Description 'HozoorYar attendance API + admin panel on port 8000' -Force | Out-Null
Write-Host "task '$taskName' registered (AtStartup, SYSTEM, unlimited runtime)"

# Stop whatever is holding 8000, then let the task own the service.
$owner = (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue).OwningProcess
if ($owner) {
    Write-Host "stopping old listener pid $owner"
    Stop-Process -Id $owner -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}
Start-ScheduledTask -TaskName $taskName
Write-Host 'task started'

Step 'verify'
Get-NetIPInterface -InterfaceAlias $IfAlias -AddressFamily IPv4 | Select-Object InterfaceAlias, Dhcp | Format-Table -AutoSize
Get-NetIPAddress -InterfaceAlias $IfAlias -AddressFamily IPv4 | Select-Object IPAddress, PrefixLength | Format-Table -AutoSize
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State | Format-Table -AutoSize
Write-Host '=== done ==='
