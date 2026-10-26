"""Balance the SDSP reserved-pool assignment on probe failure and channel remove."""
from pathlib import Path
import hashlib
import json
import subprocess

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path(__file__).resolve().parent
private = Path('/mnt/e/edk2-samurai-out/kernel186')
path = k / 'drivers/misc/fastrpc.c'
before = path.read_bytes()
assert hashlib.sha256(before).hexdigest() == 'a15e99ea6c420fd5d42ac91d3990fca1cba9762d1a51eacd80ad05383bed7a41'
value = before.decode()
marker = '\tu64 dma_mask;\n'
assert value.count(marker) == 1
value = value.replace(marker, marker + '''	phys_addr_t reserved_pool_phys;
	size_t reserved_pool_size;
	u64 reserved_pool_perms;
''')
marker = 'static int fastrpc_rpmsg_probe(struct rpmsg_device *rpdev)\n'
helpers = '''static int fastrpc_assign_reserved_pool(struct device *dev,
					struct fastrpc_channel_ctx *cctx)
{
	struct resource res;
	u64 src_perms = BIT(QCOM_SCM_VMID_HLOS);
	int ret;

	if (!cctx->vmcount)
		return 0;

	ret = of_reserved_mem_region_to_resource(dev->of_node, 0, &res);
	if (ret)
		return 0;

	ret = qcom_scm_assign_mem(res.start, resource_size(&res), &src_perms,
				  cctx->vmperms, cctx->vmcount);
	if (ret)
		return ret;

	/* SCM returns the new owner mask only after a successful transition. */
	cctx->reserved_pool_phys = res.start;
	cctx->reserved_pool_size = resource_size(&res);
	cctx->reserved_pool_perms = src_perms;

	return 0;
}

static int fastrpc_unassign_reserved_pool(struct device *dev,
					  struct fastrpc_channel_ctx *cctx)
{
	struct qcom_scm_vmperm perm = {
		.vmid = QCOM_SCM_VMID_HLOS,
		.perm = QCOM_SCM_PERM_RWX,
	};
	int ret;

	if (!cctx->reserved_pool_size)
		return 0;

	ret = qcom_scm_assign_mem(cctx->reserved_pool_phys,
				  cctx->reserved_pool_size,
				  &cctx->reserved_pool_perms, &perm, 1);
	if (ret) {
		dev_err(dev, "failed to reclaim reserved pool: %d\\n", ret);
		return ret;
	}

	cctx->reserved_pool_size = 0;
	return 0;
}

'''
assert value.count(marker) == 1
value = value.replace(marker, helpers + marker)
old = '''	if (domain_id == SDSP_DOMAIN_ID) {
		struct resource res;
		u64 src_perms;

		err = of_reserved_mem_region_to_resource(rdev->of_node, 0, &res);
		if (!err) {
			src_perms = BIT(QCOM_SCM_VMID_HLOS);

			err = qcom_scm_assign_mem(res.start, resource_size(&res), &src_perms,
				    data->vmperms, data->vmcount);
			if (err)
				goto err_free_data;
		}

	}
'''
new = '''	if (domain_id == SDSP_DOMAIN_ID) {
		err = fastrpc_assign_reserved_pool(rdev, data);
		if (err)
			goto err_free_data;
	}
'''
assert value.count(old) == 1
value = value.replace(old, new)
old = 'err_free_data:\n\tkfree(data);\n\treturn err;\n'
assert value.count(old) == 1
value = value.replace(old, 'err_free_data:\n\tfastrpc_unassign_reserved_pool(rdev, data);\n\tkfree(data);\n\treturn err;\n')
old = '\tof_platform_depopulate(&rpdev->dev);\n\n\tfastrpc_channel_ctx_put(cctx);'
assert value.count(old) == 1
value = value.replace(old, '\tfastrpc_unassign_reserved_pool(&rpdev->dev, cctx);\n\tof_platform_depopulate(&rpdev->dev);\n\n\tfastrpc_channel_ctx_put(cctx);')
path.write_text(value)
diff = subprocess.check_output(['git', 'diff', '--', 'drivers/misc/fastrpc.c'], cwd=k, text=True)
header = '''Subject: [PATCH] misc: fastrpc: reclaim the SDSP reserved pool at teardown

SDSP probe assigns the reserved DMA pool away from HLOS but neither its
failure path nor rpmsg remove restores the ownership. A second SLPI boot
then requests a transition from HLOS and fails with EINVAL repeatedly.
Track the successful SCM transition and reclaim this pool on probe unwind
and channel removal. Keep failed transitions visible and retain their
ownership bookkeeping; never infer success from an SCM error.

---

'''
patch = ref / 'fastrpc-reserved-pool-lifecycle.patch'
patch.write_text(header + diff)
p = subprocess.run(['perl', 'scripts/checkpatch.pl', '--no-signoff', '--strict', str(patch)],
                   cwd=k, capture_output=True)
(private / 'fastrpc-checkpatch-private.log').write_bytes(p.stdout + p.stderr)
report = dict(stage=186, source_before_sha256=hashlib.sha256(before).hexdigest(),
    source_after_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), checkpatch_exit=p.returncode,
    sdsp_pool_ownership_tracked=True, remove_and_probe_unwind_reclaim=True,
    reclamation_failure_reported_not_hidden=True, no_nv_or_firmware_changes=True,
    runtime_deployed=False)
(ref / 'fastrpc-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
if p.returncode:
    print(p.stdout.decode(errors='replace'))
    raise SystemExit(p.returncode)
