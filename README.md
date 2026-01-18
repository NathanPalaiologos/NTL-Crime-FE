## Illumi-Naughty

### Idea

Use **exogenous moon phase** shocks to study how **nighttime light** relates to **crime**, and how the moonlight effect differs between **bright vs dark** counties.

### Data

* **County-month crime** (2012–2021, rich breakdowns: property/violent, burglary/robbery/theft, weapon types, clearance).
* **VNP46A3 monthly NTL** (Black Marble) aggregated to county-month + QA.
* Main sample: **2013-01 to 2020-12** (2012 used to build baseline; 2021 as robustness).

### Key variables

* `Y_ct`: asinh/log(1+crime) (primary: property & violent index).
* `NTLBaseline_ct`: **previous-year mean NTL** for the county (predetermined exposure).
* `Moon_t`: **astronomical moon illumination** (exogenous).
* `MoonExp_ct = Moon_t × NightLength_ct` (night length from latitude+month; boosts spatial exposure, still exogenous).
* `HQShare_ct`: satellite quality share (control + HQ-only robustness).
* (Optional) NOAA **temp/precip** controls.

### Main regression (identification)

County FE + year-month FE:

$$
Y_{c,t} = \alpha_c + \delta_t + \theta ,(MoonExp_{c,t}\times NTLBaseline_{c,t}) + controls + \varepsilon_{c,t}
$$

Interpretation:

* `θ < 0`: artificial light substitutes for moonlight (moon matters less in bright places).
* `θ > 0`: moonlight effects amplify with brightness (opportunity/nightlife channel).

### Outputs

* Main: property vs violent.
* Heterogeneity: burglary/robbery/theft + weapon types.
* Robustness: high reporting completeness, HQ-only, add weather, optional clear-sky check.


