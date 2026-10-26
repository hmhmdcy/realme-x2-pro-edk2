from pathlib import Path
import difflib, hashlib, json, re, shutil, tarfile

stage = Path('/home/cy122/pmos-samurai-kernel111')
baseline = Path('/home/cy122/pmos-samurai-kernel109')
out = Path('/mnt/e/edk2-samurai-out/kernel111')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel111')
assert not stage.exists()
assert not (out/'source-files').exists()
archive = out/'sensor-sources-readonly.tar'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '06895411b1295d8c9bf897c73f4151660ae36bc68d4d9a65e7eb2752baa4b405'
with tarfile.open(archive) as t:
    members = t.getmembers()
    skipped = [dict(name=m.name, type=str(m.type)) for m in members if not (m.isfile() or m.isdir())]
    (out/'source-special-files-not-restored.json').write_text(json.dumps(skipped, indent=2)+'\n')
    t.extractall(out/'source-files', members=[m for m in members if m.isfile() or m.isdir()], filter='data')
sources = out/'source-files/k111-sensor-sources-readonly'
for line in (sources/'SHA256SUMS').read_text().splitlines():
    sha, name = line.split('  ', 1)
    path = sources/name
    assert path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == sha
assert all(line.endswith(': OK') for line in (sources/'sources-after-check.txt').read_text().splitlines())
assert len((sources/'sources-after-check.txt').read_text().splitlines()) == 4
stage.mkdir()
for name in ['kernel', 'initramfs']:
    shutil.copytree(baseline/name, stage/name, symlinks=True)
# A failed persistent-root handoff keeps independent USB diagnostics only.
init = stage/'initramfs/init'
text = init.read_text()
start = text.index('# Wi-Fi firmware/NV copies and services remain in RAM')
end = text.index('\necho\necho "=============================================="', start)
text = text[:start] + '# No automatic radio startup in diagnostic fallback.\n' + text[end:]
init.write_text(text)

changes = {}
def edit(name, transform):
    p = stage/'kernel'/name
    before = p.read_text()
    after = transform(before)
    assert after != before
    p.write_text(after)
    changes[name] = dict(before=hashlib.sha256(before.encode()).hexdigest(),
                         after=hashlib.sha256(after.encode()).hexdigest())
    patch = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                    fromfile='a/'+name, tofile='b/'+name))
    (ref/(p.name+'.patch')).write_text(patch)

def dts(text):
    needle = '\t\tsamurai_rmtfs_mem: rmtfs-dynamic {'
    assert text.count(needle) == 1
    heap = '''\t\t/* Stock FastRPC heap: 16 MiB, below 4 GiB in EFI-described HLOS RAM. */
\t\tsamurai_fastrpc_heap: fastrpc-shared-pool {
\t\t\tcompatible = "shared-dma-pool";
\t\t\treusable;
\t\t\tsize = <0x0 0x1000000>;
\t\t\talignment = <0x0 0x400000>;
\t\t\talloc-ranges = <0x0 0xc0000000 0x0 0x30000000>;
\t\t};

'''
    text = text.replace(needle, heap+needle)
    old = '&remoteproc_slpi {\n\tstatus = "disabled";\n};'
    new = '''/* Registered but not auto-booted: first SLPI experiment is explicit. */
&remoteproc_slpi {
\tfirmware-name = "qcom/sm8150/realme/samurai/slpi.mdt";
\tstatus = "okay";

\tglink-edge {
\t\tfastrpc {
\t\t\tmemory-region = <&samurai_fastrpc_heap>;
\t\t\t/* Stock adsprpc: HLOS, SSC_Q6, ADSP_Q6; no modem access. */
\t\t\tqcom,vmids = <3 5 6>;
\t\t};
\t};
};'''
    assert text.count(old) == 1
    return text.replace(old, new)

def pas(text):
    block = re.search(r'static const struct qcom_pas_data sdm845_slpi_resource_init = \{.*?\n\};', text, re.S)
    assert block
    manual = block.group().replace('sdm845_slpi_resource_init', 'sm8150_slpi_resource_init')
    assert manual.count('.auto_boot = true') == 1
    manual = manual.replace('.auto_boot = true', '.auto_boot = false')
    text = text[:block.end()] + '\n\n' + manual + text[block.end():]
    old = '{ .compatible = "qcom,sm8150-slpi-pas", .data = &sdm845_slpi_resource_init }'
    assert text.count(old) == 1
    return text.replace(old, old.replace('sdm845_slpi_resource_init', 'sm8150_slpi_resource_init'))

def rpc(text):
    # Robin Snyders' v2 submission, 2026-10-03: sensors use the physical remote heap.
    old = '\tif (ctx->fl->sctx->sid)\n\t\terr = fastrpc_buf_alloc(ctx->fl, dev, pkt_size, &ctx->buf);'
    assert text.count(old) == 1
    return text.replace(old, old.replace('ctx->fl->sctx->sid)', 'ctx->fl->sctx->sid && ctx->fl->pd != SENSORS_PD)'))

def pdmap(text):
    block = re.search(r'static const struct qcom_pdm_domain_data \*sm8150_domains\[\] = \{.*?\n\};',text,re.S)
    assert block and '&slpi_root_pd' not in block.group()
    old = block.group()
    assert old.count('\t&cdsp_root_pd,') == 1
    new = old.replace('\t&cdsp_root_pd,', '\t&cdsp_root_pd,\n\t&slpi_root_pd,\n\t&slpi_sensor_pd,')
    for filename, subdomain in [('slpir.jsn','root_pd'),('slpius.jsn','sensor_pd')]:
        data = json.loads((sources/'firmware'/filename).read_text())
        assert data['sr_domain'] == dict(soc='msm',domain='slpi',subdomain=subdomain,qmi_instance_id=90)
    return text.replace(old,new)

edit('arch/arm64/boot/dts/qcom/sm8150-samurai.dts', dts)
edit('drivers/remoteproc/qcom_q6v5_pas.c', pas)
edit('drivers/misc/fastrpc.c', rpc)
edit('drivers/soc/qcom/qcom_pd_mapper.c', pdmap)
config = stage/'kernel/.config'
text = config.read_text()
old = 'CONFIG_INITRAMFS_SOURCE="/home/cy122/pmos-samurai-kernel109/initramfs"'
assert text.count(old) == 1
config.write_text(text.replace(old, 'CONFIG_INITRAMFS_SOURCE="/home/cy122/pmos-samurai-kernel111/initramfs"'))
shutil.copy2(baseline/'kernel/.config', out/'config-before')
shutil.copy2(baseline/'kernel/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', out/'dtb-before')
(out/'source-change-manifest.json').write_text(json.dumps(changes, indent=2)+'\n')
(ref/'candidate-scope.json').write_text(json.dumps(dict(
    baseline=109, candidate=111, slpi_auto_boot=False,
    diagnostic_fallback_auto_radio=False, rootfs_reformatted=False,
    stock_sources_read_only_verified=4,
    fastrpc_remote_heap_bytes=0x1000000, heap_vmids=[3,5,6],
    source_files_changed=list(changes), tested_on_device=False), indent=2)+'\n')
print('SENSOR_CANDIDATE111_SOURCES_PREPARED; baseline unchanged; no device writes')
