"""Freeze only existing source inputs. Does not bind a runtime transaction."""
from pathlib import Path
import hashlib, json
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
rows = {
    'device_delivery': ('charging-session-20261023/usb-irq-protection-restart-candidate/delivery.json', '6187ea66cedfb7eaf747f0894ec17d54da2cd278e3ef0460cf002ee7a3579ad2'),
    'device_contract': ('charging-session-20261023/usb-irq-protection-restart-candidate/prepare-contract.json', '13bc81d89bfe34e573b4a23287c7841c67cd82c563cfc3266004b9ab3eba0914'),
    'device_common': ('charging-session-20261023/usb-irq-protection-restart-candidate/common.py', '715db6d6219fa69f4ffaacce53084d03ba085aa2c7d24d4cf41ba58f00b2d9c6'),
    'quiesce': ('charging-session-20261023/usb-irq-protection-restart-candidate/eud-quiesce.py', '43c5bd1952949504e918c660b208ca6bb45cfa103be9c9be575268b64ef9036e'),
    'restart': ('charging-session-20261023/usb-irq-protection-restart-candidate/eud-restart.py', '56a58c08bd3f79813d95955279f3ad07f7338d522239d32a7cfec4ea8d3b05be'),
    'stage_proof': ('charging-oem-audit-20261023/irq-cohort-postboot-host-candidate/stage-proof.py', '85c9cd2b728a547ba434322d47cc15d4aeb228ae77afebeb7edff1bd0422e093'),
    'stage_proof_frozen': ('charging-oem-audit-20261023/irq-cohort-postboot-host-candidate/stage-proof-frozen.json', '6f5a5b7e6ad2dcbb8a51115864571b44f1561eaddd4848a03f0687328fc4a3d3'),
    'postboot_host_delivery': ('charging-oem-audit-20261023/irq-cohort-postboot-host-candidate/delivery.json', '8a4301cb9850dcab65069f6ec0e2ca47b8be72b1fcbb2676357863518f640d2a'),
    'operator_delivery': ('charging-oem-audit-20261023/usb-irq-protection-fastboot-candidate/delivery.json', 'ff8051089bc6306f9cfbf29914f8531fa4d627cc0661a5b7e7401ec42f362a41'),
    'key_transport': ('kernel184/host.py', '7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c'),
    'baseline_controller': ('charging-oem-audit-20261023/image502-logdump-activation-candidate/controller.py', '7c1a3d9a02f63020ec5bbcd921c2f8e2a488166d2f7ce9cd4f6b7476c5ba64dd'),
    'baseline_remote': ('charging-session-20261023/gauge-image501-activation-candidate/remote.py', 'ba0a070fc88777e548a4ae93479f47b621cfb5392b4f9b9f088a840d23001a8a'),
    'baseline_supervisor': ('charging-oem-audit-20261023/usb-irq-protection-stage-host-candidate-r2/supervisor.py', 'b29ab985159ecc911571514cdc5fa72a1a44886037e35ff024dfa6fe623440cc'),
}
pins = {}
for name, (relative, digest) in rows.items():
    path = REF / relative; raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest, name
    pins[name] = dict(path=path.as_posix(), sha256=digest, bytes=len(raw))
camera = Path('E:/edk2-samurai-out/kernel481/formal-expected-private.json'); raw = camera.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705'
pins['camera_wrapper'] = dict(path=camera.as_posix(), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
(HERE / 'source-pins.json').write_text(json.dumps(pins, indent=2) + '\n', newline='\n')
print(json.dumps(dict(source_only=True, source_pins=len(pins), runtime_material_created=False)))
