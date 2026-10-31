# Conditional comparison: B excitation, fitted RTN

|Topology|RB Ω|RE Ω|Added resistor Ω|Historical-code RMSE mV|Min code margin|2/3 margin|5/6 margin|1/2 margin|0–50°C span mV|BR variation span mV|Excitation span mV|Range reachable|Compatibility|Recommendation|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
|C|22000|0|0|276.69|0|0|3|0|49.87|1070.45|124.33|FAIL|NOT VERIFIED|reject range|
|C|22000|100|0|272.35|0|0|3|0|49.77|1033.36|125.22|FAIL|NOT VERIFIED|reject range|
|C|22000|220|0|266.99|0|0|3|0|49.66|987.12|126.19|FAIL|NOT VERIFIED|reject range|
|C|22000|470|0|251.72|0|0|3|0|49.41|898.52|128.17|FAIL|NOT VERIFIED|reject range|
|C|22000|1000|0|188.60|0|0|3|0|48.77|723.53|125.06|FAIL|NOT VERIFIED|reject range|
|C|22000|2200|0|132.49|4|17|4|92|3.23|391.48|89.70|PASS conditional|NOT VERIFIED|bench candidate only|
|A|29900|0|0|6.36|2|3|2|14|43.49|1274.35|154.55|PASS conditional|NOT VERIFIED|bench candidate only|
|B|29900|100|0|7.45|2|4|2|14|43.39|1241.99|155.03|PASS conditional|NOT VERIFIED|bench candidate only|
|B|29900|220|0|10.68|2|4|2|14|43.21|1210.27|155.71|PASS conditional|NOT VERIFIED|bench candidate only|
|B|29900|470|0|19.40|2|4|2|14|42.83|1128.47|157.12|PASS conditional|NOT VERIFIED|bench candidate only|
|B|29900|1000|0|39.50|3|4|3|14|42.06|943.33|156.49|PASS conditional|NOT VERIFIED|bench candidate only|
|B|29900|2200|0|177.14|1|14|1|72|2.80|458.05|92.54|FAIL|NOT VERIFIED|reject range|
|C|33000|0|0|93.97|2|3|2|13|41.27|1325.21|161.00|PASS conditional|NOT VERIFIED|bench candidate only|
|C|33000|100|0|97.71|2|4|2|12|41.12|1300.15|161.54|PASS conditional|NOT VERIFIED|bench candidate only|
|C|33000|220|0|102.19|2|3|2|12|40.96|1259.88|162.17|PASS conditional|NOT VERIFIED|bench candidate only|
|C|33000|470|0|111.50|2|3|2|13|40.67|1168.65|163.45|PASS conditional|NOT VERIFIED|bench candidate only|
|C|33000|1000|0|131.14|2|3|2|13|39.99|977.14|164.09|PASS conditional|NOT VERIFIED|bench candidate only|
|C|33000|2200|0|212.84|0|14|0|68|2.38|468.93|92.96|FAIL|NOT VERIFIED|reject range|
|C|47000|0|0|442.68|2|3|2|10|36.04|1449.19|180.44|PASS conditional|NOT VERIFIED|bench candidate only|
|C|47000|100|0|445.80|1|2|1|10|35.93|1405.65|180.85|PASS conditional|NOT VERIFIED|bench candidate only|
|C|47000|220|0|449.54|1|2|1|11|35.82|1357.74|181.36|PASS conditional|NOT VERIFIED|bench candidate only|
|C|47000|470|0|457.30|2|3|2|10|35.58|1253.31|182.40|PASS conditional|NOT VERIFIED|bench candidate only|
|C|47000|1000|0|473.65|2|3|2|10|34.96|1051.47|184.59|PASS conditional|NOT VERIFIED|bench candidate only|
|C|47000|2200|0|510.08|0|13|0|61|1.05|505.36|94.20|FAIL|NOT VERIFIED|reject range|
|C|68000|0|0|814.25|1|3|1|9|32.99|1513.72|197.64|PASS conditional|NOT VERIFIED|bench candidate only|
|C|68000|100|0|816.67|2|2|2|9|32.92|1466.83|197.93|PASS conditional|NOT VERIFIED|bench candidate only|
|C|68000|220|0|819.56|2|2|2|9|32.83|1412.52|198.31|PASS conditional|NOT VERIFIED|bench candidate only|
|C|68000|470|0|825.57|1|2|1|10|32.61|1309.16|199.19|PASS conditional|NOT VERIFIED|bench candidate only|
|C|68000|1000|0|838.21|1|2|1|9|31.75|1102.59|200.87|PASS conditional|NOT VERIFIED|bench candidate only|
|C|68000|2200|0|866.35|0|0|0|28|1.68|529.50|94.96|FAIL|NOT VERIFIED|reject range|
|D|29900|0|47000|33.22|2|5|2|19|51.63|1018.97|113.96|PASS conditional|NOT VERIFIED|bench candidate only|
|D|29900|0|100000|18.88|3|4|3|16|47.96|1141.74|132.37|PASS conditional|NOT VERIFIED|bench candidate only|
|D|29900|0|220000|10.72|2|4|2|15|45.70|1212.32|143.52|PASS conditional|NOT VERIFIED|bench candidate only|

Historical-code RMSE is diagnostic, not a refit score for each retrofit. Temperature/BR/excitation spans use each design’s nominal reselected integer codes; no recoding under perturbation. Additional resistor is B–RTN. Code margins are distances between nearest target codes, not known classification intervals. Range reachability means continuous sweep endpoints cover all targets; integer quantisation residuals are separately in JSON. All hardware/device-limit checks remain NOT VERIFIED.
