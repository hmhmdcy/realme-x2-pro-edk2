"""Compare paired images and independent meshes; no optical accuracy assertion."""
from pathlib import Path
import hashlib, json, struct, sys
import numpy as np

HERE = Path(__file__).resolve().parent
P = Path('E:/edk2-samurai-out/kernel327')
run = sys.argv[1] if len(sys.argv) > 1 else 'r1'
cases = json.loads((HERE / 'cases.json').read_text())
observation = json.loads((P / ('probe-' + run + '-observation.json')).read_text())
assert observation['state']['summary']['passed'] and not observation['worker_live']
matrix = np.array([[.299, .587, .114], [-.168736, -.331264, .5], [.5, -.418688, -.081312]])

def read(path, height):
    raw = path.read_bytes()
    assert len(raw) == 320 * height * 3 // 2
    a = np.frombuffer(raw, np.uint8)
    y = a[:320 * height].reshape(height, 320).astype(float)
    uv = a[320 * height:].reshape(height // 2, 160, 2).repeat(2, 0).repeat(2, 1).astype(float)
    return np.dstack((y, uv)), hashlib.sha256(raw).hexdigest()

def sample(mesh, tx, ty):
    ix = np.floor(tx).astype(int); iy = np.floor(ty).astype(int)
    fx = tx - ix; fy = ty - iy
    def v(dx, dy): return mesh[np.clip(iy + dy, 0, 12), np.clip(ix + dx, 0, 16)]
    return (v(0, 0) * (1-fx) + v(1, 0) * fx) * (1-fy) + (v(0, 1) * (1-fx) + v(1, 1) * fx) * fy

rows = []
for name, case in cases.items():
    if case['kind'] != 'unit': continue
    factory_name = name.replace('-unit-', '-factory-')
    tag = name.rsplit('-', 1)[1]
    model = case['model']
    width, height = map(int, case['sensor_size'].split('x'))
    oh = int(case['output'].split('x')[1])
    if model == 's5kgw1':
        baseline_path = P.parent / 'kernel325/images-r3' / ('s5kgw1-off-' + tag + '-private.nv12')
        old_factory_path = P.parent / 'kernel325/images-r3' / (case['variant'] + '-' + tag + '-private.nv12')
    elif model == 'imx471':
        baseline_path = P.parent / 'kernel324/capture-r3' / ('imx471-off-' + tag + '-private.nv12')
        old_factory_path = P.parent / 'kernel324/capture-r3' / ('sunny_imx471-' + tag + '-private.nv12')
    else:
        baseline_path = P.parent / 'kernel323/capture-r1/off-private.nv12'
        old_factory_path = P.parent / 'kernel323/capture-r1/factory-private.nv12'
    base, _ = read(baseline_path, oh)
    factory, factory_sha = read(P / ('images-' + run) / (factory_name + '-private.nv12'), oh)
    _, old_factory_sha = read(old_factory_path, oh)
    actual, unit_sha = read(P / ('images-' + run) / (name + '-private.nv12'), oh)
    y, x = np.indices((oh, 320))
    mask = (x >= 8) & (x < 312) & (y >= 8) & (y < oh-8)
    edges = np.zeros((oh, 320), dtype=bool)
    edges[:, 1:] = np.max(abs(np.diff(base, axis=1)), axis=2) > 4
    for shift in range(-6, 7): mask &= ~np.roll(edges, shift, axis=1)
    resets = np.flatnonzero(np.median(abs(np.diff(base[:, :, 0], axis=0)), axis=1) > 8) + 1
    for row in resets: mask[abs(y-row) <= 3] = False
    assert mask.any()
    rgb = np.clip((base - np.array([0, 128, 128])) @ np.linalg.inv(matrix).T / 255, 0, 1)
    linear = np.where(rgb <= .04045, rgb/12.92, ((rgb + .055)/1.055)**2.4)
    models = []
    for selected, image in [(factory_name, factory), (name, actual)]:
        raw = (P / (selected + '-mesh-private.bin')).read_bytes()
        cw, ch, ox, oy, level = struct.unpack_from('<HHHHB', raw, 8)
        meshes = np.array(struct.unpack_from('<884H', raw, 24)).reshape(4, 13, 17) / 1024
        tx = ((x+.5) * (width/2)/320 + ox)/cw
        ty = ((y+.5) * (height/2)/oh + oy)/ch
        gain = np.dstack([sample(meshes[0], tx, ty), sample((meshes[1]+meshes[2])/2, tx, ty), sample(meshes[3], tx, ty)])
        corrected = np.clip(linear * gain, 0, 1)
        encoded = np.where(corrected <= .0031308, 12.92*corrected, 1.055*corrected**(1/2.4)-.055)*255
        predicted = np.clip(encoded @ matrix.T + np.array([0, 128, 128]), 0, 255)
        error = abs(image-predicted)[mask]
        models.append(dict(case=selected, mean_error=float(error.mean()),
            p99_error=float(np.quantile(error, .99)), maximum_error=float(error.max())))
    delta = abs(actual-factory)[mask]
    log = observation['logs']['capture-' + name + '.log']
    assert f'LSC_SENSOR width={width} height={height}' in log and 'LSC_PATTERN_ACTIVE toggled=1' in log
    rows.append(dict(variant=case['variant'], model=model, mode=tag, sensor_size=[width, height],
        unit_differs_from_factory=unit_sha != factory_sha, changed_components=int(np.count_nonzero(delta)),
        mean_absolute_yuv_difference=float(delta.mean()), compared_pixels=int(mask.sum()),
        factory_identical_to_retained_reference=factory_sha == old_factory_sha,
        actual_sensor_mode_confirmed=True, approximate_models=models,
        excluded_baseline_reset_rows=resets.tolist()))
report = dict(stage=327, run=run, cases=rows, actual_installed_ipa_to_isp=True,
    individual_values_temporarily_applied=True, explicit_unit_illuminant=0,
    all_four_cameras_unit_chain_exercised_including_wide322=True,
    supplier_binding_verified=False, default_tuning_changed=False, normal_light_optical_calibration=False,
    model_limit='Bilinear spatial and mean-green Bayer approximation; NV12-inverted retained baseline and clipping limit accuracy',
    passed=all(r['unit_differs_from_factory'] and r['changed_components'] > 0 for r in rows))
(HERE / 'unit-image-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
assert report['passed']
