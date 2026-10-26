$ErrorActionPreference='Stop'
$dest='E:\edk2-samurai-out\kernel79'
$files=[ordered]@{
 'first-dmesg.txt.gz'='994ec0968f9424e316707d46f837a7f70b20eca988186b1f13345c784a3da20f'
 'mounted-dmesg.txt.gz'='6875123850704731d8c53dc2e6f492c21fd2637e4c4db5db460a7326e417c901'
 'complete-dmesg.txt.gz'='44c82ae69b3854a568150b041e2e6a747b46b6f43e3eedfbd88ad0094a9f2b46'
 'mounted-kms.txt'='6e0803a387a72be9ef82680f820e1dfb622403a83cf47d61d0ce56e1e54bbb2d'
 'mounted-state.txt'='7ead5b9a6dc5a78fb81f7cdf66df5e50841ef5221ab8e203965fed2244e9028c'
 'mounted-clocks.txt'='dde449be0f690b7561efa7238ffa0ef6d5dffaa02211a3badd14afe6135b3cff'
 'complete-kms.txt'='591b311c4a37a99161d8f0c891e310dfab89a9bb1ae882184255c7cc28912ec4'
 'mp-observation.txt'='6ea916ae6e0a1bfba6a9292b35e9c1289bde39d8bd6893810e282fde022eeace'
 'mp-followup.txt'='3ac6834760eaf38926236be8dbf78ea742e88be9b929b74d6726c24189a129e8'
 'pageflip.txt'='ed9ad2d9544c90fe0cc5156d911b93b30bcd036d7ca06c8ec7ca769f2d5b883f'
}
foreach ($name in $files.Keys) {
 $target=if ($name -eq 'mounted-state.txt') {'mounted-drm-state.txt'} else {$name}
 if (!(Test-Path -LiteralPath "$dest\$target")) {
  & "$PSScriptRoot\..\kernel72\scp-usb.ps1" "root@169.254.42.1:/tmp/k79-$name" "$dest\$target"
 }
 if ((Get-FileHash -LiteralPath "$dest\$target").Hash.ToLowerInvariant() -ne $files[$name]) {throw "Remote/local digest mismatch: $name"}
}
