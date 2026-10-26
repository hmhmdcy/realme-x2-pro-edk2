from pathlib import Path
import importlib.util,subprocess
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel217')
spec=importlib.util.spec_from_file_location('strict_usb217',Path(__file__).resolve().parent.parent/'kernel188/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport);transport.PRIVATE=PRIVATE
def ssh(command,*,input=None,timeout=60):
    try:return transport.ssh(command,input=input,timeout=timeout)
    except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
        (PRIVATE/'transport-last-failure-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise RuntimeError('Authenticated217 operation failed; private diagnostics retained') from None
