# PCB connectivity extraction — PDF page 1, DigitalPotentiometer block

Source: supplied Heat_Vent_Test_Rig_Test, SCH1(1).pdf, version V1.0, updated 2026-02-17. This is the upper PCB, not the external Veroboard. Both text extraction and rendered page were inspected.

| Function | Pin | U1 connection | U10 connection | Evidence status |
|---|---:|---|---|---|
| VCC | 9 | +5V | +5V | confirmed schematic |
| GND | 10 | 24V/local GND | 24V/local GND | confirmed schematic |
| common LO0–5 | 16 | 24V/local GND | 24V/local GND | confirmed schematic |
| HI0–2 | 20 | +5V | +5V | confirmed schematic |
| HI3–5 | 15 | +5V | +5V | confirmed schematic |
| W0 | 19 | SS-B → U11 pin 6 | ES-R → U13 pin 4 | confirmed schematic |
| W1 | 18 | ES-C → U11 pin 5 | SS-U → U13 pin 3 | confirmed schematic |
| W2 | 17 | ES-F → U11 pin 4 | ES-V → U13 pin 2 | confirmed schematic |
| W3 | 14 | SS-J → U11 pin 3 | no-connect | confirmed schematic |
| W4 | 13 | ES-K → U11 pin 2 | no-connect | confirmed schematic |
| W5 | 12 | ES-N → U11 pin 1 | no-connect | confirmed schematic |
| A0 | 1 | local GND | local GND | confirmed schematic |
| A1 | 2 | local GND | local GND | confirmed schematic |
| A2 | 3 | local GND | +5V | confirmed schematic |
| SDA | 4 | I2C_SDA; R1 4.7k pull-up | I2C_SDA; R4 4.7k pull-up | confirmed schematic |
| SCL | 5 | I2C_SCL; R2 4.7k pull-up | I2C_SCL; R3 4.7k pull-up | confirmed schematic |
| I/O0–3 | 6,7,8,11 | no-connect | no-connect | confirmed schematic |
| decoupling | — | C8 100nF +5V–local GND | C9 100nF +5V–local GND | confirmed schematic |

U11/U13 each also exposes local GND. P1 connects 0V and 24V. U117 has input VIN at 24V, GND at 0V, output +Vo at +5V and −Vo at 24V/local GND. Therefore +5V means **+5 V relative to local GND**, not +5 V relative to the input 0V net. Nominal system coordinates: input 0V=0, 24V=+24, +5V rail=+29. Shift all nodes by −24 V for SPICE: local GND=0, input 0V=−24, +5V=+5. No polarity inversion is introduced by this coordinate shift.

Unknown: physical continuity/pinout on Veroboard; relationship of HVAC RTN to local GND; actual rail measurements, DS3930 resistance and wiper-resistance tolerance, and manufacturer limits. Notes specify C=Sensor, E=RTN, B via 29.9k from W. These external connections are assumed in simulations without swapping C/E. RTN is a distinct node whose DC potential must be considered as an uncertain nuisance parameter. No PCB net proves that RTN equals input 0V, local GND or +5V.

Datasheet retrieval attempted at https://www.analog.com/media/en/technical-documentation/data-sheets/DS3930.pdf; HTTP 403. Web tool also returned errors; subsequent GitHub search stalled and was cancelled. No manufacturer model/limits are claimed verified. Reconstructed equivalent uses explicit assumed resistance parameters and 256 integer positions; its results are conditional until datasheet values are checked. Missing Phase 2 does not prevent this minimum reconstruction.
