"""Apply the public patch to the archived original and compare build inputs."""
from pathlib import Path
import hashlib, json, shutil, subprocess, tempfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel149')
out=Path('/mnt/e/edk2-samurai-out/kernel149')
patch=ref.parent.parent/'linux-port/patches/0015-mesa-turnip-a640-vm-bind-iova-alignment.patch'
original=out/'tu_knl_drm.cc.original'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(original)=='0f88da327cd39abe01b87521158367939f511d06356519120e60a99c0dfd9982'
assert digest(out/'libvulkan_freedreno.so.fixed')=='97f3638851b534070f649fabfbdbb3d330b4ad0e2b0ea93b78026ad71d78fb5e'
with tempfile.TemporaryDirectory(prefix='k149-mesa-patch-') as d:
    base=Path(d);source=base/'src/freedreno/vulkan/tu_knl_drm.cc'
    source.parent.mkdir(parents=True);shutil.copy2(original,source)
    subprocess.run(['git','apply','--check',str(patch)],cwd=base,check=True)
    subprocess.run(['git','apply',str(patch)],cwd=base,check=True)
    assert digest(source)=='3729ad81907bd4b8d515c950c54e667fccbb280fb6b58f40decb40577c7853e0'
    s=source.read_text()
    assert s.count('util_vma_heap_alloc(&dev->vma, size, alignment)')==2
    assert s.count('util_vma_heap_alloc_addr(&dev->vma, client_iova, size)')==1
    report=dict(public_patch_applies=True,patched_source_matches_compiled_candidate=True,
        patch_sha256=digest(patch),patched_source_sha256=digest(source),
        automatic_low_and_high_allocations_aligned=True,explicit_address_path_preserved=True,
        candidate_binary_hash_verified=True)
(ref/'patch-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
