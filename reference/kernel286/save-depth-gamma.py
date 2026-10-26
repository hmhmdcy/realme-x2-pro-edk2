"""Save and independently reconstruct the verified 286 candidate patch."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent
previous=ROOT.parent/'kernel285/save-cst.py'
s=previous.read_text()
replacements=[
    ("/mnt/e/edk2-samurai-out/kernel285","/mnt/e/edk2-samurai-out/kernel286"),
    ("BASE='af9e2a02365a2ec1a19d3cc42da5c65e84c244c4'","BASE='d1a5f84405cfa774765e9b8ffabd6d1533dec2b6'"),
    ('samurai-vfe175-cst285','samurai-vfe175-depth-gamma286'),
    ("['Makefile','camss-vfe-175-cst.c','camss-vfe-175-cst.h','camss-vfe-175-pixel.c']",
     "['Makefile','camss-vfe-175-round.c','camss-vfe-175-round.h','camss-vfe-175-gamma.c','camss-vfe-175-gamma.h','camss-vfe-175-pixel.c']"),
    ('cst-host-tests-validation','depth-gamma-host-tests-validation'),
    ('vfe175-cst-candidate','vfe175-depth-gamma-candidate'),
    ('cst-checkpatch','depth-gamma-checkpatch'),('cst-commit-message','depth-gamma-commit-message'),
    ('cst-commit-validation','depth-gamma-commit-validation'),('stage=285','stage=286')]
for old,new in replacements:
    assert old in s,old;s=s.replace(old,new)
start=s.index("message='''");end=s.index("'''",start+11)+3
s=s[:start]+'''message="""media: qcom: camss: configure VFE175 FULL output depth and Gamma16

Use distinct FULL Y/C round-clamp enables, preserving crop/scaler bits.
Validate 8/10-bit endpoints before MMIO and round the 10-bit pipeline
to the NV12 output depth, with interleaved chroma and matched pattern.

Build 65-knot standard transfer curves for the native 64-entry Gamma16
tables. Reject nonrepresentable signed deltas before MMIO, fill inactive
banks using explicit DMI addresses, restore shared port state, then publish
bank selection and enable. Keep the current RDI resources and public
parameters unchanged; this is pre-stream setup, not a per-frame DMI API.

Clear all processing enables on FULL stop or startup failure. Physical
color/bank order, DMI behavior and complete pipeline validation remain
pending before exposing PIX.

Signed-off-by: Samurai Builder <samurai@localhost>
"""''' +s[end:]
s=s.replace("dem=prefix+'camss-vfe-175-demosaic.c'", "dem=prefix+'camss-vfe-175-demosaic.c'")
# CST is also unchanged; add it to the independent preservation check.
needle="report=dict(stage=286"
assert s.count(needle)==1
s=s.replace(needle,"cst=prefix+'camss-vfe-175-cst.c'\nassert subprocess.check_output(['git','-C',str(TREE),'show',BASE+':'+cst])==(TREE/cst).read_bytes()\n"+needle)
s=s.replace('demosaic_source_identical=True,','demosaic_source_identical=True,cst_source_identical=True,')
exec(compile(s,str(previous),'exec'),globals())
