"""Fit channel/offset hypotheses on part of the patches, then inspect holdout.

This is observational inference, not an independently established hardware
equation. Factory coefficients and inferred private mappings are not printed.
"""
from pathlib import Path
import itertools,json,math
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;fixture=json.loads((P/'fixture-private.json').read_text());patches=json.loads((P/'patches-private.json').read_text())
A=fixture['quantized_cst_matrix'];cst=fixture['cst'];v=fixture['quantized_cv_luma'];yo=fixture['quantized_cv_y_offset']
allperm=list(itertools.permutations(range(3)))
train=[i for i in range(48) if i//8 in [1,2] or (i//8==0 and i%8 in [1,3,5])];hold=[i for i in range(48) if i not in train]
def source(i):
 row,col=divmod(i,8);y=16+32*col if not row else 128 if row<4 else 64 if row==4 else 192
 u,w=(128,128) if not row else (96+32*(col%3),96+32*(row-1)) if row<4 else (64+48*(col%4),208-48*(col//2))
 return [y,u,w]
def roundvalue(value):return math.floor(value+.5)
def component(mode,rgb,offset_scale):
 if mode==3:return [0.,0.,0.]
 if mode==4:return [x/2 for x in rgb]
 if mode==5:return [rgb[2],rgb[1],rgb[0]]
 if mode>=6:
  sign=1 if mode==6 else -1
  return [min(1023,max(0,x+sign*k*offset_scale)) for x,k in zip(rgb,[-64,32,96])]
 return rgb
rank=[]
for input_scale in [1,4]:
 for inp in allperm:
  for pre_round in [False,True]:
   pres=[]
   for i in range(48):
    x=source(i);x=[x[k]*input_scale-cst['s_tab'][j] for j,k in enumerate(inp)]
    raw=[sum(A[j*3+k]*x[k] for k in range(3))/1024+cst['o_tab'][j] for j in range(3)]
    pres.append([min(cst['c_x1_tab'][j],max(cst['c_x0_tab'][j],roundvalue(z) if pre_round else z)) for j,z in enumerate(raw)])
   for rgbperm in allperm:
    rgbs=[[p[j] for j in rgbperm] for p in pres]
    for lumaperm in allperm:
     lum=[v[j] for j in lumaperm]
     for offset_scale in [1.,.25,.0625]:
      def predict(i,mode):return roundvalue((sum(a*b for a,b in zip(lum,component(mode,rgbs[i],offset_scale)))/256+yo)/4)
      errors=[predict(i,mode)-patches['0-'+str(mode)][i]['median'][0] for i in train for mode in range(1,8)]
      score=sum(e*e for e in errors)
      if len(rank)<12 or score<=rank[-1]['score']:
       held=[predict(i,mode)-patches['0-'+str(mode)][i]['median'][0] for i in hold for mode in range(1,8)]
       rank.append(dict(score=score,train_max=max(map(abs,errors)),holdout_score=sum(e*e for e in held),holdout_max=max(map(abs,held)),input_scale=input_scale,input_permutation=inp,pre_round=pre_round,rgb_permutation=rgbperm,luma_permutation=lumaperm,offset_scale=offset_scale))
       rank.sort(key=lambda r:r['score']);rank=rank[:12]
(P/'luma-model-ranking-private.json').write_text(json.dumps(dict(training_patch_indices=train,holdout_patch_indices=hold,models=rank),indent=2)+'\n')
report=dict(stage=400,training_patches=len(train),holdout_patches=len(hold),modes=7,best_training_squared_error=rank[0]['score'],best_training_max_error=rank[0]['train_max'],best_holdout_squared_error=rank[0]['holdout_score'],best_holdout_max_error=rank[0]['holdout_max'],equal_training_best_models=sum(r['score']==rank[0]['score'] for r in rank),model_selected_only_on_training=True,multiple_model_ambiguity_preserved=True,independent_hardware_equation_not_claimed=True,completed=True)
(HERE/'luma-inference.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
