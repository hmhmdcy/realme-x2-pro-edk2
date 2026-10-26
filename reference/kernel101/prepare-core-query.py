from pathlib import Path
import difflib, shutil
k=Path('/home/cy122/x2pro-linux/linux')
root=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel101')
path=k/'sound/soc/qcom/qdsp6/q6core.c'
before=path.read_text()
assert 'samurai_api' not in before
assert not (out/'q6core-before.c').exists()
(out/'q6core-before.c').write_text(before)
after=before.replace('case APR_BASIC_RSP_RESULT:{\n', 'case APR_BASIC_RSP_RESULT:{\n\t\tif (data->payload_size < sizeof(*result))\n\t\t\treturn -EINVAL;\n',1)
after=after.replace('fwk = data->payload;\n', '''fwk = data->payload;
		if (data->payload_size < sizeof(*fwk) ||
		    fwk->num_services > (data->payload_size - sizeof(*fwk)) /
					sizeof(fwk->svc_api_info[0]))
			return -EINVAL;
''',1)
after=after.replace('v = data->payload;\n', '''v = data->payload;
		if (data->payload_size < sizeof(*v) ||
		    v->num_services > (data->payload_size - sizeof(*v)) /
				      sizeof(v->svc_api_info[0]))
			return -EINVAL;
''',1)
after=after.replace('case AVCS_CMDRSP_ADSP_EVENT_GET_STATE:\n', 'case AVCS_CMDRSP_ADSP_EVENT_GET_STATE:\n\t\tif (data->payload_size < sizeof(u32))\n\t\t\treturn -EINVAL;\n',1)
addition='''/* A reply-backed diagnostic for this handset, without opening a PCM route. */
static ssize_t samurai_api_show(struct device *dev,
			       struct device_attribute *attr, char *buf)
{
	struct q6core_svc_api_info afe = { .api_version = U32_MAX,
					 .api_branch_version = U32_MAX };
	struct q6core_svc_api_info asm_info = { .api_version = U32_MAX,
					      .api_branch_version = U32_MAX };
	int ret;

	ret = q6core_get_svc_api_info(4, &afe);
	if (ret)
		return ret;
	if (afe.api_version == U32_MAX || afe.api_branch_version == U32_MAX)
		return -ETIMEDOUT;
	ret = q6core_get_svc_api_info(7, &asm_info);
	if (ret)
		return ret;
	if (asm_info.api_version == U32_MAX ||
	    asm_info.api_branch_version == U32_MAX)
		return -ETIMEDOUT;

	return sysfs_emit(buf, "native_version_reply service4_api=%u service4_branch=%u service7_api=%u service7_branch=%u\\n",
			  afe.api_version, afe.api_branch_version,
			  asm_info.api_version, asm_info.api_branch_version);
}
static DEVICE_ATTR_RO(samurai_api);

'''
after=after.replace('static int q6core_probe(struct apr_device *adev)\n',addition+'static int q6core_probe(struct apr_device *adev)\n',1)
after=after.replace('static int q6core_probe(struct apr_device *adev)\n{\n','static int q6core_probe(struct apr_device *adev)\n{\n\tint ret;\n\n',1)
after=after.replace('init_waitqueue_head(&g_core->wait);\n\treturn 0;', '''init_waitqueue_head(&g_core->wait);
	if (of_machine_is_compatible("realme,samurai")) {
		ret = device_create_file(&adev->dev, &dev_attr_samurai_api);
		if (ret) {
			kfree(g_core);
			g_core = NULL;
			return ret;
		}
	}
	return 0;''',1)
after=after.replace('struct q6core *core = dev_get_drvdata(&adev->dev);\n\n\tif (core->fwk_version_supported)', 'struct q6core *core = dev_get_drvdata(&adev->dev);\n\n\tif (of_machine_is_compatible("realme,samurai"))\n\t\tdevice_remove_file(&adev->dev, &dev_attr_samurai_api);\n\n\tif (core->fwk_version_supported)',1)
assert after!=before and after.count('DEVICE_ATTR_RO(samurai_api)')==1
path.write_text(after)
(root/'reference/kernel101/q6core-samurai-query.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/sound/soc/qcom/qdsp6/q6core.c',tofile='b/sound/soc/qcom/qdsp6/q6core.c')))
for name in ('Image-adsp','dtb-adsp','cpio-after','config-after','kernel-validation.json'):
    shutil.move(out/name,out/(name+'.before-core-query'))
print('BOUNDED_NATIVE_CORE_QUERY_PREPARED')
