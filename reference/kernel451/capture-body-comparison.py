"""Phone-side A/B/A body; importing this file performs no device operations."""
from pathlib import Path
import hashlib
import json
import os
import pwd
import re
import runpy
import shutil
import signal
import subprocess
import time

PREFIX = "k451-proxy-comparison-"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def charging():
    implementation=runpy.run_path("/usr/sbin/samurai-charging")
    metadata=implementation["verify"]()
    for name,row in metadata["modules"].items():
        implementation["loaded_matches"](Path(row["target"]),name.replace("-","_"))
    source=Path("/sys/class/power_supply/samurai-usb-input")
    charger=Path("/sys/class/power_supply/mp2650-input")
    udcs=list(Path("/sys/class/udc").iterdir())
    assert len(udcs)==1 and (udcs[0]/"state").read_text().strip()=="configured"
    gadgets=[p for p in Path("/sys/kernel/config/usb_gadget").iterdir()
             if (p/"UDC").read_text().strip()]
    assert len(gadgets)==1
    declarations=list((gadgets[0]/"configs").glob("*/MaxPower"))
    assert len(declarations)==1
    kind=re.search(r"\[([^]]+)\]",(source/"usb_type").read_text())
    assert kind and int((source/"online").read_text())==1
    return dict(
        manifest_sha256=sha("/usr/share/samurai-charging/manifest.json"),
        notes={name:sha(Path("/sys/module",name,"notes/.note.gnu.build-id"))
               for name in ["samurai_usb_input","samurai_gauge_protection","samurai_mp2650"]},
        limits={name:int((charger/name).read_text()) for name in
                ["input_current_limit","constant_charge_current","constant_charge_voltage"]},
        source_type=kind[1],source_budget_ua=int((source/"current_max").read_text()),
        native_udc_allowance_ua=int((source/"input_current_limit").read_text()),
        gadget_maxpower_ma=int(declarations[0].read_text()),
        service_enabled=Path("/etc/runlevels/default/samurai-charging").is_symlink(),
        native_retained=Path("/sys/module/samurai_usb_input/parameters/native_retained").read_text().strip()=="Y",
        control_enabled=Path("/sys/module/samurai_mp2650/parameters/control").read_text().strip()=="Y",
    )

def packages():
    result={}
    for block in Path("/lib/apk/db/installed").read_text().split("\n\n"):
        fields=dict(line.split(":",1) for line in block.splitlines() if ":" in line)
        name=fields.get("P","")
        if name.startswith(("libcamera","samurai-camera-")):
            result[name]=fields["V"]
    return result

def validate_handoff(root,state):
    root=Path(root)
    plan=json.loads((root/"comparison-plan-private.json").read_text())
    handoff=json.loads((root/"handoff-private.json").read_text())
    assert root.name==plan["window_id"]==handoff["window_id"] and root.name.startswith(PREFIX)
    assert handoff["schema"]=="samurai-camera-handoff-v1" and handoff["window_owner"]=="camera"
    assert handoff["fresh_preflight_verified"] is True and handoff["issued_at_utc"]
    assert handoff["formal_baseline_sha256"]==sha(root/"baseline-private.json")
    assert os.uname().release==plan["kernel_release"]
    guard=Path(handoff["boot_guard_path"])
    assert guard.is_absolute() and guard.read_bytes()==Path("/proc/sys/kernel/random/boot_id").read_bytes()
    assert json.loads((root/"proof.json").read_text())["boot_guard"]==str(guard)
    for name,digest in json.loads((root/"manifest.json").read_text()).items():
        path=Path(name)
        assert not path.is_absolute() and ".." not in path.parts
        assert sha(root/path)==digest
    snapshot=charging()
    assert snapshot==handoff["charging"],"New handoff charging snapshot does not match actual state"
    assert all(snapshot[key] for key in ["service_enabled","native_retained","control_enabled"])
    state["comparison_charging_before"]=snapshot
    state["comparison_formal_library_before"]=sha("/usr/lib/libcamera.so.0.7.2")
    assert state["comparison_formal_library_before"]==handoff["formal_library_sha256"]
    state["comparison_packages_before"]=packages()
    state["comparison_window_id"]=root.name
    return plan

def related(userroot):
    result=[]
    text=str(userroot)
    for entry in Path("/proc").glob("[0-9]*"):
        try:
            stat=(entry/"stat").read_text().rsplit(")",1)[1].split()
            if stat[0]=="Z":
                continue
            exe=os.readlink(entry/"exe")
            args=[part.decode() for part in (entry/"cmdline").read_bytes().split(bytes([0])) if part]
            if exe.startswith(text+"/") or (args and any(arg==text for arg in args)):
                result.append(int(entry.name))
        except (OSError,UnicodeDecodeError):
            pass
    return result

def proc_identity(pid):
    path=Path("/proc",str(pid))
    values=dict(line.split(":",1) for line in (path/"status").read_text().splitlines() if ":" in line)
    assert all(int(value)==10000 for value in values["Uid"].split())
    assert int(values["CapEff"].strip(),16)==0
    fields=(path/"stat").read_text().rsplit(")",1)[1].split()
    assert fields[0]!="Z"
    return path,int(fields[19]),values

def live_witness(log,userroot,expected_proxy_sha,expected_core_sha):
    before=time.monotonic_ns()
    text=Path(log).read_text(errors="replace")
    app={int(value) for value in re.findall(r"APPLICATION_PROCESS pid=(\d+)",text)}
    ipa={int(value) for value in re.findall(r"IPA stats pid=(\d+)",text)}
    if len(app)!=1 or len(ipa)!=1:
        return None
    app_pid=next(iter(app));ipa_pid=next(iter(ipa))
    assert app_pid!=ipa_pid
    application,app_start,_=proc_identity(app_pid)
    worker,worker_start,_=proc_identity(ipa_pid)
    expected_core=str(userroot/"lib/libcamera.so.0.7.2")
    expected_module=str(userroot/"ipa/ipa_camss_vfe.so")
    assert expected_core in (application/"maps").read_text()
    worker_maps=(worker/"maps").read_text()
    assert expected_core in worker_maps and expected_module in worker_maps
    actual_exe=os.readlink(worker/"exe")
    assert actual_exe==str(userroot/"proxy/camss_ipa_proxy")
    actual_hash=sha(worker/"exe")
    assert actual_hash==expected_proxy_sha
    assert proc_identity(app_pid)[1]==app_start and proc_identity(ipa_pid)[1]==worker_start
    latest=Path(log).read_text(errors="replace")
    frames=[int(value) for value in re.findall(r"GST_IMAGE frame=(\d+) ",latest)]
    return dict(
        uid=10000,effective_capabilities=0,application_pid=app_pid,ipa_pid=ipa_pid,
        application_start_ticks=app_start,ipa_start_ticks=worker_start,
        actual_ipa_exe=actual_exe,actual_ipa_exe_sha256=actual_hash,
        actual_candidate_core_mapping=True,actual_ipa_module_mapping=True,
        core_sha256_verified_before_start=expected_core_sha,
        witness_started_ns=before,witness_finished_ns=time.monotonic_ns(),
        last_consumed_frame_at_witness_end=max(frames,default=-1),passed=True,
    )

def run_comparison(root,state,save,status,idle,core):
    root=Path(root);plan=json.loads((root/"comparison-plan-private.json").read_text())
    assert [row["name"] for row in plan["segments"]]==["A1","B","A2"]
    assert [row["kind"] for row in plan["segments"]]==["old","new","old"]
    state["captures"]={};state["sustained"]={};state["comparison_observer_used"]=False
    account=pwd.getpwuid(10000)
    nodes=[p for p in Path("/sys/class/video4linux").glob("v4l-subdev*")
           if (p/"name").read_text().startswith("s5kgw1 ")]
    devices=[p for p in Path("/sys/bus/i2c/drivers/s5kgw1").iterdir() if (p/"of_node").exists()]
    assert len(nodes)==len(devices)==1
    camera_id="/base"+str((devices[0]/"of_node").resolve()).split("/base",1)[1]
    # Keep executable/module/library/profile paths identical in all three cases.
    # This exact prefix permits reuse of the byte-identical 450 user launcher.
    userroot=Path("/run/user/10000")/("k450-user-"+root.name)
    state["comparison_userroot"]=str(userroot)
    for segment in plan["segments"]:
        name=segment["name"];case=root/name;case.mkdir()
        assert not userroot.exists() and not related(userroot)
        userroot.mkdir(mode=0o700);child=None
        try:
            for folder in ["lib","ipa","proxy","captures"]:
                (userroot/folder).mkdir(mode=0o700)
            for relative,digest in plan["common_payload"].items():
                target=userroot/relative
                shutil.copyfile(root/relative,target)
                target.chmod(0o700 if relative=="gst-sustained" else 0o600)
                assert sha(target)==digest
            worker=userroot/"proxy/camss_ipa_proxy"
            shutil.copyfile(root/segment["proxy_payload"],worker);worker.chmod(0o700)
            assert sha(worker)==segment["proxy_sha256"]
            for library in ["libcamera","libcamera-base"]:
                (userroot/f"lib/{library}.so.0.7").symlink_to(f"{library}.so.0.7.2")
            for path in [userroot,*userroot.rglob("*")]:
                if path.is_symlink():
                    os.lchown(path,10000,account.pw_gid)
                else:
                    os.chown(path,10000,account.pw_gid)
            env=dict(os.environ)
            for variable in list(env):
                if variable=="LD_LIBRARY_PATH" or variable.startswith(("LIBCAMERA_","CAPTURE_","GST_")):
                    env.pop(variable,None)
            env.update(
                LIBCAMERA_LOG_LEVELS="*:INFO,CamssVfe:DEBUG,IPACamss:DEBUG",
                LD_LIBRARY_PATH=str(userroot/"lib"),LIBCAMERA_IPA_MODULE_PATH=str(userroot/"ipa"),
                LIBCAMERA_IPA_PROXY_PATH=str(userroot/"proxy"),
                LIBCAMERA_CAMSS_VFE_PROFILE=str(userroot/"factory-s5kgw1-private.yaml"),
                LIBCAMERA_IPA_FORCE_ISOLATION="1",CAPTURE_DIR=str(userroot/"captures"),
                PIPELINE_FIXTURE_TIMEOUT_SECONDS="25",GST_TARGET_FRAMES="180",
                GST_SENSOR_NODE="/dev/"+nodes[0].name,
            )
            completed_before=status()["completed"];launched=time.monotonic()
            logfile=case/"client.log"
            with logfile.open("xb") as output:
                child=subprocess.Popen(
                    [str(root/"pipeline-fixture"),"/dev/media0",str(root/"user-launcher.py"),
                     str(userroot),"gst-sustained",camera_id,"1920","1080"],
                    env=env,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
                save("capture-"+name,client_pid=child.pid)
                witness=None;deadline=time.monotonic()+15
                while witness is None and child.poll() is None and time.monotonic()<deadline:
                    witness=live_witness(logfile,userroot,segment["proxy_sha256"],
                                         plan["common_payload"]["lib/libcamera.so.0.7.2"])
                    if witness is None:
                        time.sleep(.05)
                assert witness and witness["passed"],"Required live /proc worker identity was not observed"
                (case/"live-proxy-private.json").write_text(json.dumps(witness,indent=2)+"\n")
                code=child.wait(timeout=40)
            text=logfile.read_text(errors="replace")
            assert code==0 and "FIXTURE_RESTORATION result=0" in text
            assert "exited=1 exit=0 signalled=0" in text
            assert len(re.findall(r"GST_RESULT frames=180 width=1920 height=1080 bus-errors=0 result=0",text))==1
            assert re.findall(r"APPLICATION_IDENTITY uid=(\d+) euid=(\d+) capeff=(\S+)",text)==[
                ("10000","10000","0000000000000000")]
            idle();current=status()
            assert not any(current[key] for key in ["failed","cancelled","first_error","fatal"])
            state["sustained"][name]=dict(
                kind=segment["kind"],frames=180,ipe_completed=current["completed"]-completed_before,
                elapsed_seconds=round(time.monotonic()-launched,3),exit_code=code,
                uid=10000,effective_capabilities=0,intentional_cancellation=False,
                proxy_sha256=segment["proxy_sha256"],live_proc_witness_passed=True,
            )
            assert state["sustained"][name]["ipe_completed"]>=180
        finally:
            if child is not None and child.poll() is None:
                os.killpg(child.pid,signal.SIGTERM)
                try:
                    child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
            deadline=time.monotonic()+6
            while related(userroot) and time.monotonic()<deadline:
                time.sleep(.05)
            assert not related(userroot),"Keep the private directory for precise residual cleanup"
            if (userroot/"captures").exists():
                shutil.copytree(userroot/"captures",case/"captures")
            assert not userroot.is_symlink() and userroot.resolve().parent==Path("/run/user/10000").resolve()
            assert userroot.name=="k450-user-"+root.name
            shutil.rmtree(userroot)
    state["candidate_final_status"]=status();state["candidate_final_core"]=core()

def finalize(root,state):
    root=Path(root)
    snapshot=charging()
    assert snapshot==state["comparison_charging_before"]
    assert sha("/usr/lib/libcamera.so.0.7.2")==state["comparison_formal_library_before"]
    assert packages()==state["comparison_packages_before"]
    devices=["ac10000.icp","acb3000.camss","ac4a000.cci","ac4b000.cci"]
    deadline=time.monotonic()+4
    while True:
        runtime={name:Path("/sys/bus/platform/devices",name,"power/runtime_status").read_text().strip()
                 for name in devices}
        if all(value=="suspended" for value in runtime.values()):
            break
        assert time.monotonic()<deadline,runtime
        time.sleep(.05)
    services={}
    for name in ["pipewire","wireplumber"]:
        found=[]
        for entry in Path("/proc").glob("[0-9]*"):
            try:
                if (entry/"comm").read_text().strip()==name and (entry/"stat").read_text().rsplit(")",1)[1].split()[0]!="Z":
                    values=dict(line.split(":",1) for line in (entry/"status").read_text().splitlines() if ":" in line)
                    assert all(int(value)==10000 for value in values["Uid"].split())
                    found.append(int(entry.name))
            except (FileNotFoundError,ProcessLookupError):
                pass
        assert len(found)==1
        services[name]=found
    userroot=Path("/run/user/10000")/("k450-user-"+root.name)
    assert not related(userroot) and not userroot.exists()
    state["comparison_charging_after"]=snapshot
    return dict(charging_equal=True,formal_library_equal=True,formal_packages_equal=True,
                camera_runtime=runtime,user_services=services,
                no_user_processes_or_directory=True,observer_used=False,passed=True)
