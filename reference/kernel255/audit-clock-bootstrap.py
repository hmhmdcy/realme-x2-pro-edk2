"""Compare documented AP bootstrap paths; never infer physical XO lock."""
from pathlib import Path
import hashlib,json,re,subprocess

ROOT=Path(__file__).resolve().parents[1]
P=Path('/mnt/e/edk2-samurai-out/kernel255')
LINUX=Path('/home/cy122/x2pro-linux/linux')


def main():
    oem=P/'oem-source'
    clk=(oem/'drivers__clk__qcom__clk-rpmh.c').read_text()
    binding=(oem/'include__dt-bindings__clock__qcom,rpmh.h').read_text()
    loader=(oem/'drivers__soc__qcom__peripheral-loader.c').read_text()
    lc=(LINUX/'drivers/clk/qcom/clk-rpmh.c').read_text()
    ld=(LINUX/'arch/arm64/boot/dts/qcom/sm8150.dtsi').read_text()
    pas=(LINUX/'drivers/remoteproc/qcom_q6v5_pas.c').read_text()
    stock=Path('/mnt/e/edk2-samurai-out/kernel253/live-device-tree-private.dtb')
    def fdt(node,key,kind='s'):
        if kind=='d':kind='u'
        return subprocess.check_output(['fdtget','-t',kind,str(stock),node,key],text=True).strip()
    mss='/soc/qcom,mss@4080000'
    assert fdt(mss,'clock-names')=='xo'
    assert fdt(mss,'qcom,proxy-clock-names')=='xo'
    assert fdt(mss,'qcom,pas-id','d')=='4'
    assert fdt(mss,'clocks','d')=='37 0'
    assert fdt('/soc/qcom,rpmhclk','phandle','d')=='37'
    assert fdt('/soc/qcom,rpmhclk','compatible')=='qcom,rpmh-clk-sm8150'
    assert re.search(r'#define RPMH_CXO_CLK\s+0\b',binding)
    assert re.search(r'DEFINE_CLK_RPMH_ARC\(sm8150, bi_tcxo, bi_tcxo_ao, "xo.lvl".*?&apps_rsc, 19200000',clk,re.S)
    assert re.search(r'sm8150_rpmh_clocks\[\].*?\[RPMH_CXO_CLK\]\s*= &clk_rpmh_bi_tcxo_div2.hw',lc,re.S)
    assert re.search(r'xo_board: xo-board.*?clock-frequency = <38400000>',ld,re.S)
    assert 'return prate / r->div;' in lc
    assert 'clk_prepare_enable(pas->xo)' in pas and 'clk_disable_unprepare(pas->xo)' in pas
    assert re.search(r'mpss_resource_init.*?\.pas_id = 4,.*?"cx",.*?"mss",',pas,re.S)
    assert 'proxy_unvote_intr_handler' in loader and 'desc->ops->proxy_unvote(desc)' in loader
    snapshots={}
    for label in ['before','active-5','active-30','active-75','after']:
        rows=json.loads((Path('/mnt/e/edk2-samurai-out/kernel242/clock-evidence')/(label+'-private.json')).read_text())
        values={}
        for line in rows['clk'].splitlines():
            fields=line.split()
            if len(fields)>8 and fields[0] in ('xo_board','bi_tcxo','bi_tcxo_ao'):
                values[fields[0]]=int(fields[4])
        snapshots[label]=values
    old=json.loads(Path('/mnt/e/edk2-samurai-out/kernel242/clock-source-audit-private.json').read_text())
    current_hash=hashlib.sha256((LINUX/'drivers/clk/qcom/clk-rpmh.c').read_bytes()).hexdigest()
    primary=json.loads((oem/'manifest.json').read_text())
    output=dict(stock_live_dt=dict(compatible=fdt(mss,'compatible'),clock_names='xo',
        proxy_clock_names='xo',proxy_regulator_names=fdt(mss,'qcom,proxy-reg-names'),
        pas_id=4,proxy_timeout_ms=int(fdt(mss,'qcom,proxy-timeout-ms','d')),
        clock_provider_compatible='qcom,rpmh-clk-sm8150',clock_selector=0),
        oem_reference_xo_nominal_hz=19200000,linux_parent_nominal_hz=38400000,
        linux_cxo_divider=2,linux_resulting_nominal_hz=19200000,
        observed_linux242_nominal_clock_snapshots=snapshots,
        linux_clock_source_matches_242_audited_hash=current_hash==old['manifest']['drivers/clk/qcom/clk-rpmh.c'],
        both_bootstrap_paths_have_xo_and_cx_mss_proxy_resources=True,
        linux_prepare_enable_and_handover_disable_present=True,
        oem_generic_proxy_unvote_interrupt_path_present=True,
        no_factor_two_mismatch_identified=True,
        primary_oem_reference_sources=primary,
        linux_source_sha256={str(f.relative_to(LINUX)):hashlib.sha256(f.read_bytes()).hexdigest()
            for f in [LINUX/'drivers/clk/qcom/clk-rpmh.c',LINUX/'drivers/remoteproc/qcom_q6v5_pas.c',LINUX/'arch/arm64/boot/dts/qcom/sm8150.dtsi']},
        source_audit_not_physical_clock_or_rf_measurement=True,
        oem_public_source_not_claimed_byte_identical_to_f16_kernel_binary=True,
        source_does_not_prove_modem_owned_rffe_lna_or_memory_initialization_equal=True)
    (ROOT/'kernel255/clock-bootstrap-validation.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:output[k] for k in ['stock_live_dt','oem_reference_xo_nominal_hz','linux_resulting_nominal_hz','observed_linux242_nominal_clock_snapshots','linux_clock_source_matches_242_audited_hash','no_factor_two_mismatch_identified']},indent=2))


if __name__=='__main__':main()
