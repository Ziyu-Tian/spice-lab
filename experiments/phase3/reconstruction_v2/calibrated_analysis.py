"""Repeat the candidate sweep under the best conditional RTN fit; separate evidence."""
from pathlib import Path
P=Path(__file__).resolve().parent
s=(P/'run.py').read_text()
core=s.split('\nfits=[]')[0].replace("P/'simulation_audit'","P/'calibrated_audit'")
exec(compile(core,str(P/'run.py'),'exec'))
f=min([x for x in json.loads((P/'reference_fits.json').read_text()) if x['model']=='B'],key=lambda x:x['RMSE_mV'])
fits=[f]
body=s[s.index('results=[]; nine=[]'):]
body=body.replace("logis=f['logIS'])","logis=f['logIS'],rtn=f['RTN'])")
body=body.replace("logis=f['logIS']) if False","logis=f['logIS'],rtn=f['RTN']) if False")
body=body.replace("logis=f['logIS']+np.linspace(-.3,.3,9)[i]","rtn=f['RTN'],logis=f['logIS']+np.linspace(-.3,.3,9)[i]")
body=body.replace("P/'optimisation.json'","P/'calibrated_optimisation.json'").replace("P/'nine_summary.json'","P/'calibrated_nine_summary.json'").replace("f'nine_","f'calibrated_nine_")
# Plot must use reference_audit for the calibration fit; candidate audit otherwise independent.
body=body[:body.index('for f in fits:\n t=np.loadtxt')]+"\nprint('DONE',counter,flush=True)\n"
exec(compile(body,str(P/'run.py'),'exec'))
