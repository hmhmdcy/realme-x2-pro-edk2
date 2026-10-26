from pathlib import Path
import difflib,hashlib,json,shutil

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel219')
for w,h,v in [(1928,1088,-1),(2304,1728,-1),(2304,1728,396),(4608,3456,-1)]:
    p=json.loads((here/f'{w}x{h}-timing-vblank{v}-validation.json').read_text())
    assert p['frame_count']==120 and not p['register_errors']
    expected=p['inferred_rate_if_vt_four_pixel_lanes']/p['hardware_line_length']/p['hardware_frame_length']
    assert abs(expected/p['fps_from_hardware_timestamps']-1)<0.001
old=(private/'candidate-source/imx471.c').read_text();new=old
replacements=[
    ('#define IMX471_REG_FLL\t\t\t\tCCI_REG16(0x0340)', '#define IMX471_REG_FLL\t\t\t\tCCI_REG16(0x0340)\n#define IMX471_REG_LLP\t\t\t\tCCI_REG16(0x0342)'),
    ('\t{ IMX471_REG_CSI_LANE_MODE, IMX471_CSI_4_LANE_MODE },','\t{ IMX471_REG_CSI_LANE_MODE, IMX471_CSI_4_LANE_MODE },\n\t{ IMX471_REG_LLP, 5120 },'),
    ('\t\t.llp = 2328,','\t\t.llp = 5120,'),
    ('\t\t.pixel_rate = 160000000,','\t\t.pixel_rate = 387200000,'),
    ('\t\t.pixel_rate = 320000000,','\t\t.pixel_rate = 326400000,'),
    ('\t\t.pixel_rate = 599040000,','\t\t.pixel_rate = 578133333,'),
    ('\t/* pixel_rate = link_freq * 2 * nr_of_lanes / bits_per_sample */\n\tpixel_rate = div_u64(IMX471_LINK_FREQ_DEFAULT * 2 * 4, 10);',
     '\t/* Pixel-array rate comes from the VT PLL, not CSI-2 throughput. */\n\tpixel_rate = mode->pixel_rate;'),
]
for before,after in replacements:
    assert new.count(before)==1,(before,new.count(before));new=new.replace(before,after)
target=private/'timing-source';assert not target.exists();target.mkdir(mode=0o700)
(target/'imx471.c').write_text(new);shutil.copyfile(private/'candidate-source/sm8150-samurai.dts',target/'sm8150-samurai.dts')
patch='Subject: [PATCH] media: imx471: report pixel-array timing from the VT PLL\n\nActive register reads and 120-frame timestamp measurements identify the\nlegacy line length as 5120. Program it explicitly, and report the VT PLL\npixel-array rates instead of serial-link throughput in all three modes.\nKeep the PLL register profiles and link frequencies unchanged.\n\n---\ndiff --git a/drivers/media/i2c/imx471.c b/drivers/media/i2c/imx471.c\n'
patch+=''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/drivers/media/i2c/imx471.c',tofile='b/drivers/media/i2c/imx471.c'))
(here/'imx471-pixel-array-timing.patch').write_text(patch)
proof=json.loads((here/'factory-mode-candidate-source-validation.json').read_text());proof['source_sha256']=hashlib.sha256(new.encode()).hexdigest()
proof.update(vt_array_rate_and_legacy_llp_crosschecked_against_active_registers_and_480_frames=True,
             pll_tables_and_link_frequencies_unchanged=True,legacy_llp_explicitly_programmed_to_observed_5120=True)
(here/'timing-candidate-source-validation.json').write_text(json.dumps(proof,indent=2)+'\n')
source=(here/'build-mode-driver.py').read_text()
# Resolve the original verified builder, then redirect only source/result paths.
namespace={'__file__':str(here/'build-mode-driver.py')}
prefix=source.split("exec(compile(text",1)[0];exec(compile(prefix,'build-generator219','exec'),namespace)
code=namespace['text']
code=code.replace("here/'factory-mode-candidate-source-validation.json'","here/'timing-candidate-source-validation.json'")
code=code.replace("candidate=private/'candidate-source'","candidate=private/'timing-source'")
code=code.replace("out=private/'candidate-build'","out=private/'timing-build'").replace("backup=private/'candidate-build-before'","backup=private/'timing-build-before'")
code=code.replace("here/'factory-mode-candidate-build-validation.json'","here/'timing-candidate-build-validation.json'")
(here/'build-timing-fix-generated.py').write_text(code)
print(json.dumps(dict(source_sha256=proof['source_sha256'],hardware_line_length=5120,array_rates=[387200000,326400000,578133333],no_pll_reprogramming_change=True)))
