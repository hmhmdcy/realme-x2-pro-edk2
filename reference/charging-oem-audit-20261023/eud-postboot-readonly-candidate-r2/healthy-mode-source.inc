full=(s.get('logical_full')==s.get('hold_requested')==s.get('full_holding')==1 and s.get('full_cause') in (1,2,3) and s.get('desired_enable')==0 and s.get('session_seconds')==0)
mode=full if any(s.get(k,0) for k in ['logical_full','hold_requested','full_holding','full_cause']) else s.get('desired_enable')==1
