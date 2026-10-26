from pathlib import Path
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel449/observe-long.py').read_text().replace('k449-lifecycle-user-','k450-stats-retirement-').replace('k449-user-','k450-user-')
needle="   result['actual_isolated_ipa_uid10000_capabilities0']=next(iter(ipa))!=int(p.name)"
assert source.count(needle)==1
source=source.replace(needle,needle+"\n   fields=(ip/'stat').read_text().rsplit(')',1)[1].split()\n   result['ipa_scheduling']=dict(allowed_cpus=data['Cpus_allowed_list'].strip(),cpu_at_read=int(fields[36]),user_ticks=int(fields[11]),system_ticks=int(fields[12]),schedstat=(ip/'schedstat').read_text().strip())")
exec(compile(source,str(HERE/'observe-long.py'),'exec'))
