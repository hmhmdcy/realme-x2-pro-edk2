from pathlib import Path
import hashlib,json,os,subprocess,time
os.umask(0o077);here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel214');root=Path('/home/cy122/x2pro-linux/libcamera214-root');assert not root.exists();root.mkdir(mode=0o700,parents=True)
apk=Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static');keys=Path('/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys')
packages=['alpine-base','build-base','abuild','coreutils','eudev-dev','glib-dev','gnutls-dev','gst-plugins-base-dev','gtest-dev','libevent-dev','libpisp-dev','libunwind-dev','libyuv-dev','linux-headers','meson','ninja','pkgconf','py3-jinja2','py3-ply','py3-pybind11-dev','py3-yaml','python3-dev','qt6-qtbase-dev','qt6-qttools-dev','yaml-dev','openssl','mesa-dev','xorgproto','patch','git']
repositories=private/'build-repositories-private.list';repositories.write_text('https://dl-cdn.alpinelinux.org/alpine/edge/main\nhttps://dl-cdn.alpinelinux.org/alpine/edge/community\n')
command=[str(apk),'--root',str(root),'--arch','aarch64','--initdb','--keys-dir',str(keys),'--repositories-file',str(repositories),'--no-cache','--no-scripts','add',*packages]
log=private/'create-build-root-private.log';assert not log.exists()
with log.open('wb') as output:
    process=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT)
    (private/'active-build-root-private.json').write_text(json.dumps(dict(pid=process.pid,phase='install-signed-arm-build-root',root=str(root),started_monotonic=time.monotonic()),indent=2)+'\n')
    result=process.wait(timeout=900)
assert result==0 and 'ERROR:' not in log.read_text(errors='replace')
assert (root/'usr/bin/g++').is_file() and (root/'usr/bin/meson').is_file()
before=Path('/proc/sys/fs/binfmt_misc/qemu-aarch64').read_text();assert 'flags: POF' in before
p=subprocess.run(['chroot',str(root),'/usr/bin/g++','--version'],capture_output=True,text=True,timeout=30)
(private/'qemu-gxx-version-private.log').write_text(p.stdout+p.stderr);assert p.returncode==0
record=dict(stage=214,signed_alpine_aarch64_build_root_installed=True,host_isolated_chroot=True,phone_not_used_for_build=True,emulated_arm_compiler_runs=True,compiler_version=p.stdout.splitlines()[0],build_dependencies=packages,private_root_only=True,no_device_mutation=True)
(private/'build-root-location-private.json').write_text(json.dumps(dict(root=str(root)),indent=2)+'\n');(here/'build-root-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
