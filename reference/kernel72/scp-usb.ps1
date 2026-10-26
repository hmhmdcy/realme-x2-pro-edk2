param([Parameter(Mandatory)][string]$Source,[Parameter(Mandatory)][string]$Destination)
$ErrorActionPreference='Stop'
$scpArgs=@('-O','-F','none','-i','E:/edk2-samurai-out/kernel72/id_ed25519',
    '-o','UserKnownHostsFile=E:/edk2-samurai-out/kernel72/known_hosts',
    '-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-o','BatchMode=yes',
    '-o','Compression=no','-o','ConnectTimeout=5','-o','ServerAliveInterval=5',
    '-o','ServerAliveCountMax=2',$Source,$Destination)
& C:\Windows\System32\OpenSSH\scp.exe @scpArgs
if ($LASTEXITCODE -ne 0) { throw "USB SCP exited $LASTEXITCODE" }
