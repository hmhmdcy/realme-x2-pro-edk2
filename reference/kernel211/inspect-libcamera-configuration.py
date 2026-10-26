from pathlib import Path
import tarfile,json
private=Path('/mnt/e/edk2-samurai-out/kernel211');out=private/'libcamera-source'
with tarfile.open(private/'libcamera-v0.7.2.tar.gz') as archive:
    members=[m for m in archive.getmembers() if m.isfile() and (m.name.endswith('/global_configuration.cpp') or m.name.endswith('/configuration.yaml') or m.name.endswith('/environment_variables.rst') or '/src/ipa/simple/algorithms/' in m.name and m.name.endswith(('/lut.cpp','agc.cpp')))]
    for member in members:
        data=archive.extractfile(member).read();relative=member.name.split('/',1)[1];p=out/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        lines=data.decode().splitlines();chosen=set()
        for i,line in enumerate(lines):
            if any(word in line for word in ['LIBCAMERA','software_isp','configuration.yaml','againMin','sensor.gain','gain', 'mode:']):chosen.update(range(max(0,i-2),min(len(lines),i+3)))
        print(json.dumps({'source':relative,'lines':{i+1:lines[i] for i in sorted(chosen)}}))
