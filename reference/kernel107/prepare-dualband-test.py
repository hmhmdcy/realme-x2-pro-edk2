from pathlib import Path
import hashlib,re
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel107';out=Path('/mnt/e/edk2-samurai-out/kernel107')
s=(out/'wpa-5g-private.conf').read_text()
frequencies=' '.join(str(f) for f in range(2412,2473,5))
assert '5180' in s
s=re.sub(r'^\s*bssid\s*=.*\n','',s,flags=re.M)
for key in ['scan_freq','freq_list']:
    s,n=re.subn(r'(^\s*'+key+r'\s*=).*$',r'\g<1>'+frequencies,s,flags=re.M)
    assert n==1 or (key=='scan_freq' and n==0)
assert '5180' not in s
p=out/'wpa-2g-private.conf';assert not p.exists();p.write_text(s);p.chmod(0o600)
n='test-final-network.sh';assert not (ref/n).exists()
s=(ref/'test-auto-network.sh').read_text().replace('k107-auto-network','k107-final-network')
s=s.replace('AUTOMATIC_FIRST_BOOT_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS','FINAL_AFTER_24G_5G_AUTH_DHCP_GATEWAY_DNS_HTTP_PASS')
(ref/n).write_text(s)
print('PRIVATE_24G_PROFILE_AND_FRESH_FINAL_5G_GUARDS_PREPARED')
