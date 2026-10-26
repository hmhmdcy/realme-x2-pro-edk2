from pathlib import Path
import hashlib, json, urllib.request
base='https://raw.githubusercontent.com/ClearStaff/linux-sm8150-mainline-hotdog/403b56c33e2ccdda25d90378970a5e5b928dee19/'
paths=['arch/arm64/boot/dts/qcom/sm8150.dtsi','arch/arm64/boot/dts/qcom/sm8150-wcd9340.dtsi','sound/soc/qcom/sm8150.c']
dest=Path('/home/cy122/x2pro-linux/refs/sm8150-audio-k102-retry1')
assert not dest.exists();dest.mkdir()
report=[]
for name in paths:
    with urllib.request.urlopen(base+name,timeout=30) as response:
        assert response.url==base+name
        data=response.read(2*1024*1024)
    license_line=data.splitlines()[0].decode()
    assert license_line in ('// SPDX-License-Identifier: GPL-2.0','// SPDX-License-Identifier: BSD-3-Clause')
    p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    report.append(dict(path=name,bytes=len(data),license=license_line,sha256=hashlib.sha256(data).hexdigest()))
(Path('/mnt/e/edk2-samurai-out/kernel102')/'soc-reference-provenance.json').write_text(json.dumps(dict(commit='403b56c33e2ccdda25d90378970a5e5b928dee19',base_url=base,files=report),indent=2)+'\n')
print('PINNED_PUBLIC_SOC_REFERENCE_FETCHED')
