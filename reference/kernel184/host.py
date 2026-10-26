"""Local WSL runner using the existing authenticated postmarketOS USB identity."""
from pathlib import Path
import subprocess

WORK = Path('/mnt/e/RealmeX2Pro edk2')
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel184')
SSH = '/mnt/c/Windows/System32/OpenSSH/ssh.exe'
SCP = '/mnt/c/Windows/System32/OpenSSH/scp.exe'
OPTIONS = ['-F', 'none', '-i', 'E:/edk2-samurai-out/kernel72/id_ed25519',
           '-o', 'UserKnownHostsFile=E:/edk2-samurai-out/kernel109/known_hosts-pmos',
           '-o', 'StrictHostKeyChecking=yes', '-o', 'IdentitiesOnly=yes',
           '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
           '-o', 'ServerAliveInterval=5', '-o', 'ServerAliveCountMax=2']


def ssh(command, *, input=None, timeout=60):
    return subprocess.run([SSH, '-T', *OPTIONS, 'root@169.254.42.1', command],
                          input=input, capture_output=True, timeout=timeout, check=True)


def upload(path, destination):
    path = Path(path).resolve()
    if not str(path).startswith('/mnt/e/'):
        raise ValueError('upload source must be on the E drive')
    windows = 'E:/' + str(path)[len('/mnt/e/'):]
    return subprocess.run([SCP, '-O', *OPTIONS, windows,
                           'root@169.254.42.1:' + destination],
                          capture_output=True, timeout=60, check=True)


def download(source, destination):
    destination = Path(destination).resolve()
    if not str(destination).startswith('/mnt/e/edk2-samurai-out/'):
        raise ValueError('device evidence must stay in the private output tree')
    windows = 'E:/' + str(destination)[len('/mnt/e/'):]
    return subprocess.run([SCP, '-O', *OPTIONS, 'root@169.254.42.1:' + source,
                           windows], capture_output=True, timeout=120, check=True)


if __name__ == '__main__':
    import sys
    PRIVATE.mkdir(parents=True, exist_ok=True)
    script = Path(sys.argv[1]).read_bytes()
    try:
        result = ssh('python3 -', input=script, timeout=55)
    except subprocess.CalledProcessError as error:
        (PRIVATE / (Path(sys.argv[1]).stem + '-failed-host-private.log')).write_bytes(error.stdout + error.stderr)
        print(error.stderr.decode(errors='replace').strip())
        raise SystemExit(error.returncode)
    (PRIVATE / (Path(sys.argv[1]).stem + '-host-private.log')).write_bytes(result.stdout + result.stderr)
    print(result.stdout.decode().strip())
