from pathlib import Path
HERE=Path(__file__).resolve().parent
s=(HERE.parent/'kernel372/check-lifecycle.py').read_text().replace('stage=372','stage=373').replace("P/'camss-icp-a5-boot.c.proposed'","P/'boot-proposed.c'")
s=s.replace("a=after.index('int camss_a5_start(')","a=after.index('static int program_hfi_parameters(')")
anchor="s=s.replace('struct camss_a5 {'"
s=s.replace(anchor,"s=s.replace('#define dev_info(...) ((void)0)','#define dev_info(...) ((void)0)\\n#define dev_err(...) ((void)0)\\n#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))')\n"+anchor)
(HERE/'check-lifecycle.py').write_text(s)
