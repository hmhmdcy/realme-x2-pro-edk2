from pathlib import Path
import hashlib,host
ref=Path(__file__).resolve().parent
host.ssh('test ! -e /usr/libexec/samurai-gnss-validation')
host.upload(ref/'geoclue-validation-client.py','/usr/libexec/samurai-gnss-validation')
host.ssh('chmod 755 /usr/libexec/samurai-gnss-validation')
print('K201_DISTINCT_DESKTOP_VALIDATION_EXECUTABLE_STAGED_NO_EXISTING_IDENTITY_USED')
