# Reconstructed equivalent circuit

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
