## Proposal

### Illumi-Naughty

**Measuring Nighttime Luminosity’s Effect on Crime: Evidence from Satellite Night Lights and Exogenous Moonlight Shocks**

### Motivation and Research Question

Nighttime lighting is often used as a proxy for human activity, economic intensity, and urban “eyes on the street.” A long-standing question is whether brighter nighttime environments deter crime (via visibility/guardianship) or increase crime opportunities (via more nighttime activity). This project studies:

1. **Does ambient nighttime illumination affect crime?**
2. **Does the effect of natural moonlight on crime vary systematically with a county’s baseline level of artificial lighting (NTL)?**

Our central hypothesis is that **natural moonlight shocks** change nighttime visibility and activity, but their impact depends on how artificially illuminated an area already is (a “substitution vs. amplification” mechanism).

---

## Data and Sample

### Crime outcomes (County × Month)

We use monthly U.S. law-enforcement reported crime counts with rich breakdowns by offense type and weapon type (e.g., property and violent index totals; robbery/burglary/theft; assaults with gun/knife/unarmed; cleared/unfounded counts). Records include agency identifiers and county FIPS codes, allowing aggregation to **county-month**.

**Sample window:** Data availability is high from **2012-01-01 to 2021-01-01**.

* **Main analysis:** **2013-01 to 2020-12** (because we define baseline NTL using the prior calendar year; 2012 is used to build the 2013 baseline).
* **Robustness:** include 2012 as a shorter-baseline variant (rolling 12-month lag), and separately test sensitivity to including early 2021.

**Quality filters (crime reporting):**

* Keep observations with no missing month flags (e.g., `month_missing = 0`), and require high reporting completeness (e.g., `number_of_months_reported ≥ 10`, with `= 12` as a stricter robustness sample).
* Aggregate across agencies within the same county-month.

### Nighttime lights (VNP46A3, Black Marble, monthly)

We use **VNP46A3 (monthly, lunar BRDF-adjusted NTL)** as the source of monthly nighttime radiance, aggregated to county-month. We also extract satellite quality indicators (e.g., high-quality retrieval share / cloud-related QA share) to address measurement reliability.

---

## Key Variable Construction

### (A) Outcome variables

We construct crime outcomes at the county-month level. Primary outcomes:

* **Property index crime** (e.g., `actual_index_property`)
* **Violent index crime** (e.g., `actual_index_violent`)

We will estimate models using:

* **asinh(count)** (preferred; handles zeros and is close to log for large counts), and
* population-normalized rates (per 100,000) as robustness.

### (B) Baseline artificial lighting exposure (low-effort, high-credibility)

To avoid simultaneity (current crime ↔ current activity ↔ current lights), we define a **predetermined baseline**:

* **Baseline NTL:**
  $$
  NTLBaseline_{c,t} = \text{mean of monthly NTL in county } c \text{ during year } (y(t)-1)
  $$
  This is fixed within a year and is based only on the previous year’s data.

(Alternative robustness: rolling 12-month lag baseline.)

### (C) Moonlight shock and enhanced spatial exposure

We want an exogenous shock with credible identification. “Observed moonlight” measures (e.g., lunar irradiance × cloud conditions) are closer to true visibility but embed weather confounding. Therefore, we will use a **two-layer approach**:

#### Main (exogenous) moonlight driver: **Astronomical moon phase**

Define a national monthly moon-phase index:

* $ Moon_t $: monthly mean moon illumination / lunar phase brightness (astronomical; common across locations).

#### Spatial exposure enhancement (recommended): **Night length by latitude**

To create county-level exposure intensity while keeping exogeneity, we scale the time shock by an externally determined “exposure” term:

* $ NightLength_{c,t}$: expected monthly average night length for county latitude (function of latitude and month only).

Then define:
$$
MoonExp_{c,t} = Moon_t \times NightLength_{c,t}
$$
This generates **cross-sectional variation in exposure** without using cloud/weather, improving power and interpretability while preserving quasi-experimental credibility.

#### Satellite-based “visible moonlight” (secondary, for robustness/validation)

We will also build:

* $ VisibleMoon_{c,t} $: county-month lunar irradiance from VNP layers (optionally multiplied by clear-sky share).
  This will *not* be the main identification source; instead it supports:
* clear-sky subsample checks, and/or
* a 2SLS robustness where astronomical $ MoonExp_{c,t} $ instruments $ VisibleMoon_{c,t}$.

---

## Empirical Strategy

### Main specification (continuous DiD: time shock × baseline exposure)

We estimate:

$$Y_{c,t} = \alpha_c + \delta_t + \beta,MoonExp_{c,t} + \theta,(MoonExp_{c,t} \times NTLBaseline_{c,t}) + \Gamma Weather_{c,t} + \Pi QA_{c,t} + \varepsilon_{c,t}$$

*  $\alpha_c$ : county fixed effects (absorbs time-invariant differences: urban form, long-run socioeconomic levels, geography).
* $\delta_t$ : year-month fixed effects (absorbs national seasonality, macro shocks, national policy changes).
* $Weather_{c,t}$ : minimal set (monthly temperature and precipitation) to block residual weather confounding.
* $ QA_{c,t}$ : satellite quality controls (e.g., high-quality retrieval share), and we also run HQ-only samples.

**Estimand of interest:** $ \theta $

* If $ \theta < 0 $: artificial lighting substitutes for natural moonlight (moonlight matters less in bright places).
* If $ \theta > 0 $: moonlight effects amplify with artificial lighting (e.g., more nighttime activity/opportunity in bright counties).

### Standard errors

We cluster standard errors at the county level; we will also report state-level clustering as robustness.

---

## Planned Heterogeneity and Mechanism Tests (Low additional effort, high payoff)

Using your crime columns, we will focus on:

1. **Property vs violent** (primary heterogeneity)
2. Specific crimes: burglary, robbery, theft, vehicle theft
3. **Weapon-specific outcomes** (gun vs knife vs unarmed) for robbery/assault to sharpen mechanism narratives
4. Clearance/unfounded outcomes as suggestive evidence on visibility and enforcement effectiveness (secondary)

---

## Robustness Checklist (Minimal but persuasive)

1. Stricter reporting completeness sample (`number_of_months_reported = 12`)
2. Alternative baseline definitions (prior-year vs rolling 12-month)
3. HQ-only satellite sample (high QA share)
4. Include/exclude pandemic period months as sensitivity
5. “Visible moonlight” validations: clear-sky subsample and/or 2SLS robustness

---

## Expected Contribution

This paper provides a credible, low-assumption quasi-experimental design linking **exogenous moonlight shocks** to crime, and shows how effects vary with **predetermined baseline artificial lighting** measured from satellite NTL. The approach leverages rich offense-level detail to distinguish deterrence vs opportunity patterns, offering actionable implications for public safety and urban lighting policy.

If you paste your **NTL table schema** (county/date/ntl + QA fields you already extracted) and confirm whether your crime data is already aggregated to county-month (or still agency-level), I can convert this into an exact “implementation plan” (variable formulas + regression table layout + recommended first outcomes to run for quickest significant results).
