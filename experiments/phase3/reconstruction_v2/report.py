from pathlib import Path
import json,csv,hashlib,tarfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
fits=json.loads((P/'reference_fits.json').read_text());f=min([x for x in fits if x['model']=='B'],key=lambda x:x['RMSE_mV'])
codes=np.array([30,41,43,50,73,75]);obs=np.array([-.792,-.726,-.709,-.681,-.560,-.548])
t=np.loadtxt(P/'reference_audit'/f['run']/'sweep.csv',delimiter=',',skiprows=1)
with (P/'calibration_operating_points.csv').open('w') as fp:
 w=csv.writer(fp);w.writerow(['code','measured_V','simulated_V','error_mV','Ib_A','Ic_A','VBE_V','VBC_V','VCE_V','local_mV_per_code','region_heuristic'])
 for c,o in zip(codes,obs):
  r=t[c];region='reverse-active/BC-forward' if r[9]>.4 and r[8]<.4 else ('both-junctions-forward' if min(r[8:10])>.4 else 'other/inspect-junctions')
  w.writerow([c,o,r[1],1000*(r[1]-o),r[5],r[6],r[8],r[9],r[10],1000*r[11],region])
fig,axs=plt.subplots(3,2,figsize=(11,11));ax=axs.ravel()
ax[0].plot(t[:,0],t[:,1]);ax[0].scatter(codes,obs,c='r');ax[0].set_ylabel('Sensor−RTN V')
ax[1].scatter(obs,t[codes,1]);ax[1].plot(obs,obs);ax[1].set_xlabel('Measured V');ax[1].set_ylabel('Simulated V')
for a,col,label in [(ax[2],5,'Ib A'),(ax[3],6,'Ic A'),(ax[4],11,'V/code')]:a.plot(t[:,0],t[:,col]);a.set_ylabel(label)
ax[5].plot(t[:,0],t[:,2],label='ideal W');ax[5].plot(t[:,0],t[:,3],label='loaded W');ax[5].plot(t[:,0],t[:,4],label='base');ax[5].legend()
for a in [ax[0],*ax[2:]]:a.set_xlabel('Integer Wiper code')
fig.tight_layout();fig.savefig(P/'conditional_calibration.png');plt.close(fig)
results=json.loads((P/'calibrated_optimisation.json').read_text())
header='|Topology|RB Ω|RE Ω|Added resistor Ω|Historical-code RMSE mV|Min code margin|2/3 margin|5/6 margin|1/2 margin|0–50°C span mV|BR variation span mV|Excitation span mV|Range reachable|Compatibility|Recommendation|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|\n'
lines=[]
for x in results:
 topology='A' if x['RB']==29900 and x['RE']==0 and not x['shape'] else ('D' if x['shape'] else ('B' if x['RB']==29900 else 'C'))
 lines.append(f"|{topology}|{x['RB']}|{x['RE']}|{x['shape']}|{x['historical_RMSE_mV']:.2f}|{x['minimum_margin']}|{x['margin23']}|{x['margin56']}|{x['margin12']}|{x['temp_span_mV']:.2f}|{x['BR_span_mV']:.2f}|{x['exc_span_mV']:.2f}|{'PASS conditional' if x['reach'] else 'FAIL'}|NOT VERIFIED|{'bench candidate only' if x['reach'] else 'reject range'}|")
(P/'comparison.md').write_text('# Conditional comparison: B excitation, fitted RTN\n\n'+header+'\n'.join(lines)+'\n\nHistorical-code RMSE is diagnostic, not a refit score for each retrofit. Temperature/BR/excitation spans use each design’s nominal reselected integer codes; no recoding under perturbation. Additional resistor is B–RTN. Code margins are distances between nearest target codes, not known classification intervals. Range reachability means continuous sweep endpoints cover all targets; integer quantisation residuals are separately in JSON. All hardware/device-limit checks remain NOT VERIFIED.\n')
(P/'equivalent.md').write_text('''# Reconstructed equivalent circuit

PCB local GND = SPICE 0; +5V = +5 V. RTN is a separate parameterized node. No circuit uses a new retrofit power connection. The RTN voltage source is a mathematical boundary condition for an existing reference of unknown potential, not a proposed added supply. Likewise HVAC sources model its excitation.

```
existing PCB: +5 -- Rupper(code) -- tap -- Rlower(code) -- local GND
                                   |
                              Rw (assumed)
                                   |
                                   W -- RB -- B
                                             | Q1 NPN
                              Sensor --------C
                                  RTN -- RE --E
optional shaping resistor: B -- Rshape -- RTN
HVAC excitation: source Es relative RTN -- Rs -- Sensor [model B]
             or compliance-limited sink Sensor → RTN [model C]
```

Rupper=Rpot(1−code/256), Rlower=Rpot code/256, integer code 0…255. A 1 µΩ numerical floor regularizes Rlower at zero; it is not a component recommendation. RE=0 is represented by 1 µΩ. Pot=50 kΩ and Rw=100 Ω are **assumed pending datasheet verification**, not extracted from the PDF. The unloaded transfer is 5 code/256. Terminal loading is fully solved through the two segments, Rw, RB and Q1. Bupper/Blower are Ohm-law behavioral resistor equivalents, not voltage buffers. Four-terminal Q syntax explicitly connects substrate to RTN to avoid an implicit PCB-ground substrate. This is a numerical generic NPN convention, not a statement about physical substrate accessibility.

Executed equivalent netlists are in each audit run.cir; original topology, emitter resistor, RB replacement and B–RTN shaping all share this diagram and differ only in listed component values. Inspect the complete parameter matrix for each run. This is a channel-level DC equivalent; I2C and decoupling are not simulated. No ideal unloaded-Wiper voltage source drives the actual load.

Model provenance: existing circuits/bjt_resistance/generic_npn.lib supplies educational IS/BF/BR/VAF/VAR/junction capacitance/resistance/time/temperature defaults. IS and BR are fitted nuisance parameters; RTN is a fitted/assumed boundary condition. They do not uniquely identify 2N5320. No verified manufacturer 2N5320 model is available. Wiper terminal absolute maximum/current, DS3930 rail range, resistance/tolerance and code-to-tap convention require direct datasheet verification; no numerical manufacturer specification is invented here. In particular, the small negative Wiper potentials at code 0 must be checked against real clamp behavior and limits before relying on endpoint predictions.
''')
counts={}
for name in ['simulation_audit','reference_audit','calibrated_audit']:
 counts[name]=len(json.loads((P/name/'matrix.json').read_text()))
(P/'audit_report.md').write_text(f'''# Additional simulation audit — append-only reconstruction v2

Original experiments/phase3/simulation_audit and development_attempt are unchanged. New directories contain the reconstructed sweeps. Process counts: {counts}; independent_checks adds 15 OP + 15 AC runs. A code sweep has 256 actual ngspice solutions, not interpolated points. Sensitivities and all numerical curves derive from executed SPICE outputs; no invented observations are appended.

PASS: connectivity extraction from PDF and explicit reference transformation; explicit C/B/E order preserved. Schematic/netlist correspondence: both pot segments at HI=+5 and LO=0, Rw→RB→B, collector Sensor, emitter via RE to RTN, shaping B→RTN. The external circuit remains assumed from notes. PDF covers only upper PCB.

PASS: representative independent_checks/checks.json compares external collector/base/Wiper and intrinsic transistor KCL (1e−8 A tolerance) and independent symmetric DC current perturbation with actual 1 Hz AC impedance (max 0.1 Ω or 0.1% tolerance). It uses codes 30,41,43,73,75 under the best conditional B fit. ngspice implicit gmin can leave sub-pA residuals. Solver convergence is not hardware validation.

FAIL: RTN=0 models fit poorly, IS reaches the allowed upper bound; they are retained as failed calibration hypotheses. FAIL: the particular compliance-knee C family fails combined six-point calibration and reachability under the examined assumptions. Its two-resistor fit is still valid. Alternative compliance laws are not excluded.

NOT VERIFIED: manufacturer DS3930 and 2N5320 electrical limits, actual resistance values, physical Veroboard pinout, measured RTN offset, board rail waveform, model uniqueness, nine-channel aggregation, precise mode thresholds and hardware validation. Thus every hardware-compatibility gate is NOT VERIFIED and no global passive optimum is approved.

Raw evidence is losslessly stored in raw_evidence.tar.gz inside each sweep audit directory, preserving run-directory names, executed netlists, raw files, logs and CSV. Extract there with `tar -xzf raw_evidence.tar.gz` before detailed inspection. Independent checks remain unpacked. Matrix JSON includes all commands, parameters and return codes. Inspect solver.log/console.log for warnings; diagnostics.json inventories warnings/errors, rather than hiding them. Source models and assumptions are in equivalent.md. SHA256SUMS is relative to reconstruction_v2; old hashes remain untouched. input_commit.txt records the input commit; the delivery Git commit records these new artifacts.

Reproduce in a fresh reconstruction_v2 copy (scripts refuse overwriting completed matrices): source .local/env.sh, run run.py, reference_analysis.py, calibrated_analysis.py, audit_checks.py, then report.py. Scripts use existing scripts/simulate_bjt_resistance.py only for parsing ngspice ASCII raw. Reproduction paths are rooted in the existing repository. Save generated directories separately before rerunning. Scripts and source PDF are hashed.
''')
# Archive exact executed evidence, including all solver diagnostics; never touch old Phase 3.
diagnostics=[]
for name in counts:
 directory=P/name
 for d in sorted(directory.glob('run_*')):
  msg=(d/'solver.log').read_text()+(d/'console.log').read_text()
  warnings=[line for line in msg.splitlines() if any(k in line.lower() for k in ['warning','error','failed','singular'])]
  if warnings:diagnostics.append(dict(audit=name,run=d.name,messages=warnings))
(P/'diagnostics.json').write_text(json.dumps(diagnostics,indent=2))
print(counts,'diagnostic runs',len(diagnostics))
