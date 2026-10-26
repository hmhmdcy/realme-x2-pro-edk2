from pathlib import Path
r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel134'
out = Path('/mnt/e/edk2-samurai-out/kernel134')
assert not (ref / 'flash-after-readonly-timeout.ps1').exists()
# The failed invocation reached only devices/getvar product, never a flash.
assert (out / 'usb-input-first-product.err').exists()
assert not list(out.glob('usb-input-first-flash-*'))
t = (ref / 'flash-validated134.ps1').read_text()
a = t.index('function Invoke-CheckedFastboot(')
b = t.index('$usb=(', a)
t = t[:a] + '''function Invoke-CheckedFastboot([string]$Name,[string[]]$Arguments,[int]$Seconds=15){
 $base="$out\\$Prefix-resume-r1-$Name"
 if(Test-Path -LiteralPath "$base.log"){throw 'Fresh operation log required'}
 & $fb @Arguments *> "$base.log"
 if($LASTEXITCODE -ne 0){throw "Fastboot $Name failed; inspect actual state before further actions"}
 return (Get-Content -LiteralPath "$base.log" -Raw)
}
''' + t[b:]
t = t.replace('$Prefix-flash-validation.json', '$Prefix-resume-r1-flash-validation.json')
(ref / 'flash-after-readonly-timeout.ps1').write_text(t)
print('K134_NATIVE_FASTBOOT_RESUME_WITH_PRIOR_SINGLE_F1_AND_NO_PRIOR_FLASH_PROOF_READY', flush=True)
