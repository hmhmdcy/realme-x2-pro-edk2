$ErrorActionPreference='Stop'
$k109out='E:\edk2-samurai-out\kernel109'
$k109ssh=@('-N','-F','none','-i','E:/edk2-samurai-out/kernel72/id_ed25519',
    '-o','UserKnownHostsFile=E:/edk2-samurai-out/kernel109/known_hosts-pmos',
    '-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-o','BatchMode=yes',
    '-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=10','-o','ServerAliveCountMax=3',
    '-R','127.0.0.1:18080:127.0.0.1:18081','root@169.254.42.1')
& C:\Windows\System32\OpenSSH\ssh.exe @k109ssh
if ($LASTEXITCODE -ne 0) {throw 'APK tunnel ended with an error'}
