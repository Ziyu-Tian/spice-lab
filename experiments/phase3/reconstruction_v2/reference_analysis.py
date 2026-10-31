"""Append-only separate reference uncertainty experiment; never touches first audit."""
from pathlib import Path
P=Path(__file__).resolve().parent
source=(P/'run.py').read_text().split('\nfits=[]')[0].replace("P/'simulation_audit'","P/'reference_audit'")
exec(compile(source,str(P/'run.py'),'exec'))
fits=[]
for m in ['B','C']:
 for initial in [0.,1.,3.]:
  def residual(x):
   t,_=run(model=m,br=10**x[0],logis=x[1],rtn=x[2]);return 1000*(t[codes,1]-obs)
  f=least_squares(residual,[1.4,-14,initial],bounds=([-2,-16,-2],[3,-12,5]),max_nfev=24,diff_step=.001)
  t,name=run(model=m,br=10**f.x[0],logis=f.x[1],rtn=f.x[2]);error=1000*(t[codes,1]-obs)
  fits.append(dict(model=m,BR=10**f.x[0],logIS=f.x[1],RTN=f.x[2],RMSE_mV=float(np.sqrt(np.mean(error**2))),errors_mV=error.tolist(),run=name))
  print(fits[-1],flush=True)
(P/'reference_fits.json').write_text(json.dumps(fits,indent=2))
(A/'matrix.json').write_text(json.dumps(manifest,indent=2))
