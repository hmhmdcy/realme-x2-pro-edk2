from pathlib import Path
import hashlib, shutil
root=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel101')
ref=root/'reference/kernel101'
source=out.parent/'kernel100/wpa-private.conf'
assert 'freq_list=5180' in source.read_text()
assert not (out/'wpa-5g-private.conf').exists()
shutil.copyfile(source,out/'wpa-5g-private.conf')
assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256((out/'wpa-5g-private.conf').read_bytes()).digest()
text=(ref/'test-recovered-network.sh').read_text().replace('k101-recovered-network','k101-recovered-network-retry1').replace('/tmp/k101-wpa-private.conf','/tmp/k101-wpa-5g-private.conf')
assert not (ref/'test-recovered-network-retry1.sh').exists()
(ref/'test-recovered-network-retry1.sh').write_text(text)
path=ref/'collect-checkpoint.sh'
text=path.read_text().replace('/tmp/k101-recovered-network/result.txt','/tmp/k101-recovered-network-retry1/result.txt').replace('/tmp/k101-recovered-network "$dir/tests/"','/tmp/k101-recovered-network /tmp/k101-recovered-network-retry1 "$dir/tests/"')
path.write_text(text)
print('VERIFIED_5G_PRIVATE_PROFILE_RETRY_PREPARED')
