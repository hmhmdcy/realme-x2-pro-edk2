param([Parameter(Mandatory)][string]$Command)
$ErrorActionPreference='Stop'
$sshArgs=@('-F','none','-i','E:/edk2-samurai-out/kernel72/id_ed25519',
    '-o','UserKnownHostsFile=E:/edk2-samurai-out/kernel72/known_hosts',
    '-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-o','BatchMode=yes',
    '-o','Compression=no','-o','ConnectTimeout=5','-o','ServerAliveInterval=5',
    '-o','ServerAliveCountMax=2','root@169.254.42.1',$Command)
& C:\Windows\System32\OpenSSH\ssh.exe @sshArgs
if ($LASTEXITCODE -ne 0) { throw "USB SSH exited $LASTEXITCODE" }
