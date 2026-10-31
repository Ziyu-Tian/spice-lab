from pathlib import Path
import json,subprocess,sys,shutil
import numpy as np
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P.parents[2]/'scripts'))
from simulate_bjt_resistance import read_raw
A=P/'independent_checks';A.mkdir(exist_ok=False)
f=min((x for x in json.loads((P/'reference_fits.json').read_text()) if x['model']=='B'),key=lambda x:x['RMSE_mV'])
s=(P/'reference_audit'/f['run']/'run.cir').read_text()
checks=[]
for code in [30,41,43,73,75]:
 values=[]
 for delta in [-1e-8,0,1e-8]:
  d=A/f'c{code}_{delta:g}';d.mkdir()
  deck=s[:s.index('.control')].replace('Vcode code 0 0',f'Vcode code 0 {code}')+f'''Iprobe rtn sensor DC {delta:.17g} AC 1
.control
set filetype=ascii
save all @q1[ib] @q1[ic] @q1[ie]
op
write op.raw all
ac lin 1 1 1
write ac.raw all
quit
.endc
.end
'''
  (d/'run.cir').write_text(deck)
  r=subprocess.run([shutil.which('ngspice'),'-b','-o','solver.log','run.cir'],cwd=d,capture_output=True,text=True)
  (d/'console.log').write_text(r.stdout+r.stderr)
  o=read_raw(d/'op.raw');a=read_raw(d/'ac.raw');v=lambda name:float(o[name][0]);sensor=v('v(sensor)');rtn=f['RTN'];ib=v('i(@q1[ib])');ic=v('i(@q1[ic])');ie=v('i(@q1[ie])')
  src=(sensor-rtn+3.4073629332569437)/6158.335720423941
  kcl=src+ic-delta
  base=(v('v(w)')-v('v(b)'))/29900-ib
  jw=(v('v(tap)')-v('v(w)'))/100
  if delta==0:
   checks.append(dict(code=code,collector_KCL_A=kcl,base_KCL_A=base,transistor_KCL_A=ib+ic+ie,wiper_KCL_A=jw-ib,AC_ohm=complex(a['v(sensor)'][0]).real,status='PASS' if max(abs(kcl),abs(base),abs(ib+ic+ie),abs(jw-ib))<1e-8 else 'FAIL'))
  values.append(sensor-rtn)
 checks[-1]['DC_incremental_ohm']=(values[2]-values[0])/2e-8
 checks[-1]['impedance_status']='PASS' if abs(checks[-1]['DC_incremental_ohm']-checks[-1]['AC_ohm'])<max(.1,abs(checks[-1]['AC_ohm'])*.001) else 'FAIL'
(A/'checks.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
