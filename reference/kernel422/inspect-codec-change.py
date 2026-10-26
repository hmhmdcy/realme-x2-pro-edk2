from pathlib import Path
import difflib
import storage
directory=storage.mount.mounted_build().parent/'source354/drivers/media/platform/qcom/camss'
private=Path('/mnt/e/edk2-samurai-out/kernel422');old=private.parent/'kernel405'
for actual,before in [('camss-icp-a5-colour.c','colour.c'),('camss-icp-a5-colour.h','include/camss-icp-a5-colour.h')]:
    a=(old/before).read_text();b=(directory/actual).read_text()
    (private/actual).write_text(b)
    patch=''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile=before,tofile=actual))
    (private/(actual+'.diff')).write_text(patch)
    print(patch[:8000])
