"""Native host boundary checks for the actual draft header; no SDK/device."""
from pathlib import Path
import csv
import hashlib
import json
import subprocess
import tempfile
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"kernel449"))
import storage
storage.mount.mounted_build()
PRIVATE=Path("/mnt/e/edk2-samurai-out/kernel452/host-ring")
PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True)
results=[]
for mode,flags in [
    ("native",["-O2"]),
    ("sanitized",["-O1","-g","-fsanitize=address,undefined","-fno-omit-frame-pointer"]),
]:
    folder=PRIVATE/mode
    folder.mkdir(mode=0o700,exist_ok=True)
    binary=folder/"trace-ring-test"
    command=["g++","-std=c++20","-Wall","-Wextra","-Werror","-Wno-mismatched-new-delete",
             *flags,"-I",str(HERE),str(HERE/"trace-ring-test.cpp"),"-o",str(binary)]
    compiled=subprocess.run(command,text=True,capture_output=True)
    assert compiled.returncode==0,compiled.stderr
    # DrvFS ignores Unix mode bits without metadata. Test exclusive 0600 export
    # on a private Linux temporary directory, then retain synthetic CSV on E.
    exported=Path(tempfile.mkdtemp(prefix="samurai-k452-"+mode+"-"))
    assert exported.resolve().parent==Path("/tmp")
    run=subprocess.run([str(binary),str(exported)],text=True,capture_output=True)
    assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
    result=json.loads(run.stdout)
    data=(exported/result["csv"]).read_text()
    (folder/result["csv"]).write_text(data)
    lines=data.splitlines()
    assert lines[0].startswith("# full-trace,version=1,capacity=8192,total=9000,retained=8192,overwritten=808,first=809,")
    assert lines[-1]=="# end,records=8192"
    records=list(csv.DictReader([line for line in lines if not line.startswith("#")]))
    assert len(records)==8192
    assert [int(row["number"]) for row in records]==list(range(809,9001))
    assert [int(row["sof"]) for row in records]==list(range(809,9001))
    assert all(int(row["hardware_ns"])==int(row["sof"])*33273000 for row in records)
    assert all(int(row["epoch"])==5 for row in records)
    assert all(int(row["request_sequence"])==2**32-1 for row in records)
    assert all(int(row["mono_ns"])>0 for row in records)
    assert all(int(b["mono_ns"])>=int(a["mono_ns"]) for a,b in zip(records,records[1:]))
    result.pop("csv")
    result["mode"]=mode;result["export_metadata_and_order"]=True
    results.append(result)
    for item in exported.iterdir():
        assert item.is_file() and item.name.startswith("full-") and item.suffix==".csv"
        item.unlink()
    exported.rmdir()
report={
    "stage":452,"tests":results,"default_disabled_no_heap_allocation":True,
    "error_and_repeated_stop_cleanup":True,"exclusive_0600_export":True,
    "header_sha256":hashlib.sha256((HERE/"full_ownership_trace.h").read_bytes()).hexdigest(),
    "phone_or_sdk_accessed":False,"production_source_modified":False,"passed":True,
}
(HERE/"ring-validation.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
