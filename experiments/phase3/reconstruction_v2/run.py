from pathlib import Path
import sys, subprocess, json, csv, hashlib, shutil
import numpy as np
from scipy.optimize import least_squares
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent; ROOT=P.parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from simulate_bjt_resistance import read_raw
A=P/'simulation_audit'; A.mkdir(exist_ok=True)
if (A/'matrix.json').exists(): raise SystemExit('Refusing overwrite')
exe=shutil.which('ngspice'); manifest=[]; counter=0
codes=np.array([30,41,43,50,73,75]); obs=np.array([-.792,-.726,-.709,-.681,-.560,-.548])
rs=6158.335720423941; es=-3.4073629332569437; knee=-.7536589987789988

def run(model='B',rb=29900,re=0,shape=0,br=20,logis=-14,rtn=0,temp=25,pot=50000,rw=100,bf=100,exc=1):
 global counter
 counter+=1; d=A/f'run_{counter:04d}';d.mkdir()
 network=f'Vexc ex rtn {es*exc:.17g}\nRs ex sensor {rs:.17g}' if model=='B' else f'Bexc sensor rtn I=max(0,{.000464957264957265*exc:.17g}+min(0,(v(sensor,rtn)-({knee:.17g}))/10))'
 # Finite floor only prevents singular endpoint resistor at code zero. 256 positions, top is 255/256.
 net=f'''PCB-ground-referenced loaded pot; external C/E preserved
Vrail hi 0 5
Vrtn rtn 0 {rtn:.17g}
Vcode code 0 0
Bupper hi tap I=v(hi,tap)/({pot:.17g}*(1-v(code)/256))
Blower tap 0 I=v(tap)/max(1e-6,{pot:.17g}*v(code)/256)
Rw tap w {rw:.17g}
Rb w b {rb:.17g}
Q1 sensor b e rtn N
Re e rtn {max(re,1e-6):.17g}
{network}
{('Rshape b rtn '+str(shape)) if shape else '* no shaping resistor'}
.model N NPN(IS={10**logis:.17g} BF={bf:.17g} BR={br:.17g} VAF=100 VAR=10 RB=100 RC=1 RE=1 CJE=10p CJC=4p TF=.4n TR=50n EG=1.11 XTI=3 TNOM=25)
.temp {temp}
.options reltol=1e-7 abstol=1e-13
.control
set filetype=ascii
save all @q1[ib] @q1[ic] @q1[ie]
dc Vcode 0 255 1
write sweep.raw all
quit
.endc
.end
'''
 (d/'run.cir').write_text(net)
 r=subprocess.run([exe,'-b','-o','solver.log','run.cir'],cwd=d,capture_output=True,text=True,timeout=15)
 (d/'console.log').write_text(r.stdout+r.stderr)
 manifest.append(dict(run=d.name,model=model,RB=rb,RE=re,shape=shape,BR=br,logIS=logis,RTN=rtn,temp=temp,pot=pot,rw=rw,BF=bf,exc=exc,returncode=r.returncode,command=[exe,'-b','-o','solver.log','run.cir']))
 raw=read_raw(d/'sweep.raw'); vs=raw['v(sensor)']-rtn
 ib=raw['i(@q1[ib])']; ic=raw['i(@q1[ic])']; ie=raw['i(@q1[ie])']
 b=raw['v(b)']; e=raw['v(e)']; w=raw['v(w)']; vbe=b-e;vbc=b-raw['v(sensor)']
 table=np.column_stack([np.arange(256),vs,np.arange(256)*5/256,w,b,ib,ic,ie,vbe,vbc,raw['v(sensor)']-e,np.gradient(vs), (raw['v(tap)']-w)/rw])
 np.savetxt(d/'sweep.csv',table,delimiter=',',header='code,sensor_RTN_V,ideal_wiper_V,loaded_wiper_V,base_V,Ib_A,Ic_A,Ie_A,VBE_V,VBC_V,VCE_V,local_V_per_code,wiper_A',comments='')
 return table,d.name

fits=[]
for m in ['B','C']:
 def residual(x):
  t,_=run(model=m,br=10**x[0],logis=x[1]);return (t[codes,1]-obs)*1000
 fit=least_squares(residual,[1.4,-14],bounds=([-2,-19],[3,-8]),max_nfev=28,diff_step=.003)
 t,name=run(model=m,br=10**fit.x[0],logis=fit.x[1]);err=(t[codes,1]-obs)*1000
 fits.append(dict(model=m,BR=10**fit.x[0],logIS=fit.x[1],RTN=0,RMSE_mV=float(np.sqrt(np.mean(err**2))),max_error_mV=float(max(abs(err))),errors_mV=err.tolist(),run=name,optimizer_success=bool(fit.success)))
(P/'fits.json').write_text(json.dumps(fits,indent=2));print('FITS',fits,flush=True)
results=[]; nine=[]
for f in fits:
 m=f['model'];base=dict(model=m,br=f['BR'],logis=f['logIS'])
 candidates=[(rb,re,0) for rb in [22000,29900,33000,47000,68000] for re in [0,100,220,470,1000,2200]]+[(29900,0,s) for s in [47000,100000,220000]]
 for rb,re,s in candidates:
  args=dict(**base,rb=rb,re=re,shape=s)
  t,name=run(**args); v=t[:,1]
  chosen=np.array([np.argmin(abs(v-x)) for x in obs]); errors=(v[chosen]-obs)*1000
  reach=bool(min(v)<=min(obs) and max(v)>=max(obs))
  cold,_=run(**args,temp=0);hot,_=run(**args,temp=50)
  spread=[]
  for multiplier in [.5,2]:
   a={**args,'br':f['BR']*multiplier}; tv,_=run(**a);spread.append(tv[chosen,1])
  ep,_=run(**args,exc=1.05);em,_=run(**args,exc=.95)
  results.append(dict(model=m,RB=rb,RE=re,shape=s,run=name,reach=reach,codes=chosen.tolist(),minimum_margin=int(min(abs(np.diff(chosen)))),margin23=int(abs(chosen[2]-chosen[1])),margin56=int(abs(chosen[5]-chosen[4])),margin12=int(abs(chosen[1]-chosen[0])),nearest_error_mV=errors.tolist(),historical_RMSE_mV=float(np.sqrt(np.mean((v[codes]-obs)**2))*1000),temp_span_mV=float(max(abs(hot[chosen,1]-cold[chosen,1]))*1000),BR_span_mV=float(max(abs(spread[1]-spread[0]))*1000),exc_span_mV=float(max(abs(ep[chosen,1]-em[chosen,1]))*1000),max_wiper_A=float(max(abs(t[:,12]))),max_wiper_V=float(max(t[:,3])),min_wiper_V=float(min(t[:,3]))))
 print('CANDIDATES',m,flush=True)
 for design in [(29900,0,0),(29900,220,0),(47000,470,0),(29900,0,100000)]:
  channels=[];names=[]
  for i in range(9):
   # Deterministic scenario; no probability or manufacturer distribution implied.
   factor=np.linspace(.5,1.5,9)[i]
   tv,name=run(**{**base,'br':f['BR']*factor},rb=design[0],re=design[1],shape=design[2],pot=50000*(.8+.05*i),rw=50+25*i,logis=f['logIS'] if False else f['logIS']) if False else run(model=m,br=f['BR']*factor,logis=f['logIS']+np.linspace(-.3,.3,9)[i],rb=design[0],re=design[1],shape=design[2],pot=50000*(.8+.05*i),rw=50+25*i)
   channels.append(tv[:,1]);names.append(name)
  data=np.array(channels).T
  dest=P/f'nine_{m}_{design[0]}_{design[1]}_{design[2]}.csv'
  np.savetxt(dest,np.column_stack([np.arange(256),data,data.mean(axis=1),data.min(axis=1),data.max(axis=1)]),delimiter=',',header='code,'+','.join('ch'+str(i+1) for i in range(9))+',hypothetical_mean,min,max',comments='')
  nine.append(dict(model=m,design=design,runs=names,spread_at_historical_codes_mV=(np.ptp(data[codes],axis=1)*1000).tolist(),worst_channel_from_mean=int(np.argmax(np.max(abs(data[codes]-data[codes].mean(axis=1)[:,None]),axis=0)))+1))
(P/'optimisation.json').write_text(json.dumps(results,indent=2));(P/'nine_summary.json').write_text(json.dumps(nine,indent=2))
(A/'matrix.json').write_text(json.dumps(manifest,indent=2))
(A/'versions.txt').write_text(subprocess.check_output([exe,'--version'],text=True)+sys.version)
(A/'input_commit.txt').write_text(subprocess.check_output(['git','rev-parse','HEAD'],text=True))
for f in fits:
 t=np.loadtxt(A/f['run']/'sweep.csv',delimiter=',',skiprows=1)
 fig,axs=plt.subplots(3,2,figsize=(11,11));ax=axs.ravel()
 ax[0].plot(t[:,0],t[:,1]);ax[0].scatter(codes,obs,c='r');ax[0].set_ylabel('Sensor−RTN V')
 ax[1].scatter(obs,t[codes,1]);ax[1].plot(obs,obs);ax[1].set_xlabel('Measured V');ax[1].set_ylabel('Simulated V')
 for a,col,label in [(ax[2],5,'Ib A'),(ax[3],6,'Ic A'),(ax[4],11,'V/code')]:a.plot(t[:,0],t[:,col]);a.set_ylabel(label)
 ax[5].plot(t[:,0],t[:,2],label='unloaded');ax[5].plot(t[:,0],t[:,3],label='loaded');ax[5].plot(t[:,0],t[:,4],label='base');ax[5].legend()
 for a in [ax[0],*ax[2:]]:a.set_xlabel('Integer code')
 fig.tight_layout();fig.savefig(P/f'calibration_{f["model"]}.png');plt.close(fig)
print('DONE',counter,flush=True)
