from pathlib import Path
import os,secrets,subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel109')
private=Path('/home/cy122/pmos-samurai-kernel109/login-pin-private.txt')
assert not private.exists()
pin=str(secrets.randbelow(90000000)+10000000)
private.write_text('User: cy122\nPhosh login PIN: '+pin+'\nSSH remains key-only.\n')
private.chmod(0o600);os.chown(private,1000,1000)
digest=subprocess.run(['openssl','passwd','-6','-stdin'],input=pin+'\n',text=True,capture_output=True,check=True).stdout.strip()
(out/'phosh-shadow-private.txt').write_text('cy122:'+digest+'\n')
(out/'login-pin-private.txt').write_text(private.read_text())
print('NUMERIC_PHOSH_LOGIN_PIN_SAVED_PRIVATELY; SSH_AUTH_UNCHANGED')
