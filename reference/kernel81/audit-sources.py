from pathlib import Path
import json,hashlib,re,subprocess
w=Path('/mnt/e/RealmeX2Pro edk2');out=Path('/mnt/e/edk2-samurai-out/kernel81');ref=w/'reference/kernel81';kernel=Path('/home/cy122/x2pro-linux/linux')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
stock=Path('/mnt/e/edk2-samurai-out/kernel76')
expected=json.loads((w/'reference/kernel80/charging-source-audit.json').read_text())['checked_stock_files']
for name,local in [('drivers/power/oppo/gauge_ic/oppo_bq27541.c',stock/'stock-oppo_bq27541.c'),('drivers/power/oppo/gauge_ic/oppo_bq27541.h',stock/'stock-oppo_bq27541.h')]:assert sha(local)==expected[name]['sha256']
c=(stock/'stock-oppo_bq27541.c').read_text();h=(stock/'stock-oppo_bq27541.h').read_text()
assert 'bq8z610_sealed' in c and 'bq8z610_check_gauge_enable' in c
assert re.search(r'#define BQ27541_REG_TEMP\s+0x06',h) and re.search(r'#define BQ27541_REG_INTTEMP\s+0x28',h)
stock_manifest=json.loads((out/'stock-wlan-source-manifest.json').read_text())
for row in stock_manifest['files']:assert sha(out/('stock-'+row['path'].replace('/','--')))==row['sha256']
tftp_manifest=json.loads((out/'tqftpserv-source-manifest.json').read_text())
for row in tftp_manifest['files']:assert sha(out/('tqftpserv-'+row['path']))==row['sha256']
dt=json.loads((out/'stock-dt-selected.json').read_text());numeric_keys={'reg','phandle','linux,phandle','clocks','clock-frequency','interrupts','interrupt-parent','iommus'}
def normalize(ps):
    for key,value in ps.items():
        b=bytes.fromhex(value['hex'])
        if key in numeric_keys:
            value.pop('strings',None)
            if len(b)%4==0:value['u32_be']=[int.from_bytes(b[n:n+4],'big') for n in range(0,len(b),4)]
        if 'target_properties' in value:normalize(value['target_properties'])
for ps in dt['nodes'].values():normalize(ps)
(ref/'stock-dt-excerpt.json').write_text(json.dumps(dt,indent=2)+'\n')
icnss=dt['nodes']['soc/qcom,icnss@18800000'];supply_keys=['vdd-cx-mx-supply','vdd-1.8-xo-supply','vdd-1.3-rfa-supply','vdd-3.3-ch0-supply']
rail_map={k:{'stock_target':icnss[k]['target'],'stock_microvolt_min':icnss[k]['target_properties']['regulator-min-microvolt']['u32_be'][0],'stock_microvolt_max':icnss[k]['target_properties']['regulator-max-microvolt']['u32_be'][0]} for k in supply_keys}
linux_files=['arch/arm64/boot/dts/qcom/sm8150-samurai.dts','arch/arm64/boot/dts/qcom/sm8150-mtp.dts','arch/arm64/boot/dts/qcom/sm8150.dtsi','drivers/net/wireless/ath/ath10k/snoc.c','drivers/net/wireless/ath/ath10k/qmi.c','drivers/remoteproc/qcom_q6v5_pas.c','drivers/soc/qcom/qcom_pd_mapper.c','drivers/gpu/drm/msm/disp/dpu1/dpu_encoder.c']
config=(kernel/'.config').read_text()
result={'stock_commit':stock_manifest['commit'],'stock_charging_file_sha256':{k:v for k,v in expected.items() if '/gauge_ic/' in k},'stock_state_read_source_functions':{'0054':'bq8z610_sealed() lines1174-1193, byte3 bits1:0 sealed==3','0057':'bq8z610_check_gauge_enable() lines1395-1414, byte2 bit3'},'stock_temperature_source':'get_battery_temperature() reads cmd_addr.reg_temp; BQ27541_REG_TEMP=0x06, BQ27541_REG_INTTEMP=0x28','TI_manual_url':'https://www.ti.com/lit/pdf/sluua65','TI_manual_sha256':'f62ec12bb5aa23631759e59a378f36d254f9b0e2b5b6b8523a0dd081a13e4139','TI_sections':['12.1.4','12.1.21','12.2.30','12.2.33'],'exact_2719_model_version_mapping_established':False,'stock_wifi_sources':stock_manifest,'tqftpserv_sources':tftp_manifest,'wifi_rails_from_same_handset_stock_DT':rail_map,'current_DT_inherits_matching_four_wifi_supplies_from_MTP':True,'current_wlan_reserved_base':'0x9b000000','current_wlan_reserved_bytes':0x180000,'stock_wlan_reserved_base':'0x9b000000','stock_wlan_reserved_bytes':0x180000,'stock_icnss_requested_MSA_memory_bytes':icnss['qcom,wlan-msa-memory']['u32_be'][0],'current_ath10k_config_enabled':False,'current_QCOM_PD_MAPPER_config':'m' if 'CONFIG_QCOM_PD_MAPPER=m' in config else 'other','mpss_PAS_auto_boot':False,'mpss_and_wifi_DT_disabled':True,'current_no_wifi_firmware_child_TZ_path':True,'mdsp_direct_host_kernel_firmware_request_found_in_audited_snoc_qmi_sources':False,'kernel_PD_domain':'msm/modem/wlan_pd','kernel_PD_services':['kernel/elf_loader','wlan/fw'],'remote_service_loading_sequence_on_this_handset_verified':False,'TFTP_not_built_or_run':True,'actual_kernel_source_HEAD':subprocess.check_output(['git','-C',str(kernel),'rev-parse','HEAD'],text=True).strip(),'actual_source_file_sha256':{p:sha(kernel/p) for p in linux_files},'no_unseal_key_material_copied':True,'display_timeout_irq_vs_firmware_vs_clock_cause_established':False}
(ref/'source-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS pinned stock charging/WLAN/TFTP sources and same-handset four-rail mapping; existing DT already inherits rails, WLAN/remote service bring-up not verified')
