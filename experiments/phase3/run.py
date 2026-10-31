"""Measurement-only excitation investigation. Run after sourcing .local/env.sh."""
from pathlib import Path
import csv, hashlib, json, platform, shutil, subprocess, sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from simulate_bjt_resistance import read_raw
P=Path(__file__).resolve().parent
A=P/'simulation_audit'
A.mkdir(exist_ok=True)
if (A/'matrix.json').exists(): raise SystemExit('Refusing to overwrite evidence; use a fresh experiment copy')
R1,R2=1170.,1750.
v1,v2=-.544,-.754
rs=(v2-v1)/(v1/R1-v2/R2)
es=v1*(1+rs/R1)
j=-es/rs
# A: finite output-resistance Norton model; B: identical Thevenin form.
# C: ideal sink until negative compliance clamp; smoothness is NOT claimed.
models={'A':f'Iexc sensor 0 DC {j:.17g}\nRout sensor 0 {rs:.17g}',
'B':f'Vexc supply 0 DC {es:.17g}\nRs supply sensor {rs:.17g}',
'C':f'Bexc sensor 0 I=max(0,{(-v1/R1):.17g}+min(0,(v(sensor)-{(v2+10*(-v1/R1+v2/R2)):.17g})/10))'}
rows=[]; matrix=[]
exe=shutil.which('ngspice')
(A/'versions.txt').write_text(subprocess.check_output([exe,'--version'],text=True)+platform.python_version())
(A/'source_commit.txt').write_text(subprocess.check_output(['git','rev-parse','HEAD'],text=True))
for model,network in models.items():
 for resistance in [0.1,500,1170,1750,3300,10000,1e9]:
  for delta in [-1e-7,0,1e-7]:
   name=f'{model}_{resistance:g}_{delta:g}'
   d=A/name; d.mkdir()
   net=f'''Excitation {model}; RTN=0 (not PCB local ground)
{network}
Rload sensor 0 {resistance:.17g}
Iprobe 0 sensor DC {delta:.17g} AC 1
.options reltol=1e-9 abstol=1e-14
.control
set filetype=ascii
op
write op.raw all
ac lin 1 1 1
write ac.raw all
quit
.endc
.end
'''
   (d/'run.cir').write_text(net)
   r=subprocess.run([exe,'-b','-o','solver.log','run.cir'],cwd=d,text=True,capture_output=True)
   (d/'console.log').write_text(r.stdout+r.stderr)
   op=read_raw(d/'op.raw'); ac=read_raw(d/'ac.raw')
   v=float(op['v(sensor)'][0]); z=complex(ac['v(sensor)'][0])
   rows.append(dict(model=model,R_ohm=resistance,probe_A=delta,V_sensor_RTN=v,Z_real_ohm=z.real,Z_imag_ohm=z.imag))
   matrix.append(dict(run=name,returncode=r.returncode,command=[exe,'-b','-o','solver.log','run.cir']))
with (A/'operating_points.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
checks=[]
for m in models:
 for resistance in [1170,1750]:
  subset=[r for r in rows if r['model']==m and r['R_ohm']==resistance]
  lo,nom,hi=subset
  target={1170:-.544,1750:-.754}[resistance]
  dc=(hi['V_sensor_RTN']-lo['V_sensor_RTN'])/2e-7
  v=nom['V_sensor_RTN']
  expected=es*resistance/(rs+resistance) if m!='C' else None
  kcl=v/resistance+(j+v/rs if m!='C' else max(0,-v1/R1+min(0,(v-(v2+10*(-v1/R1+v2/R2)))/10)))
  checks.append(dict(model=m,R=resistance,predicted_V=v,error_mV=1000*(v-target),dc_incremental_ohm=dc,ac_incremental_ohm=nom['Z_real_ohm'],kcl_A=kcl,status='PASS' if abs(v-target)<.0001 and abs(dc-nom['Z_real_ohm'])<.1 and abs(kcl)<1e-9 else 'FAIL'))
(A/'checks.json').write_text(json.dumps(checks,indent=2))
(A/'matrix.json').write_text(json.dumps(matrix,indent=2))
(A/'fitted_parameters.json').write_text(json.dumps(dict(series_R_ohm=rs,thevenin_V=es,norton_sink_A=j,C_sink_A=-v1/R1,C_knee_V=v2+10*(-v1/R1+v2/R2),C_compliance_slope_S=.1),indent=2))
(A/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(P)}\n' for f in sorted(P.rglob('*')) if f.is_file() and f.name!='SHA256SUMS'))
print(json.dumps(checks,indent=2))
