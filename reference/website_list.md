# Website List for Reference and Data Access

## Option 1: Offenses Known Data (1960-2024 Monthly)

- **Description**: This dataset contains monthly data on offenses known to law enforcement from 1960 to 2024. Aggregate counts by agency-month. Does NOT include incident time.
- **Access Link**: <https://www.openicpsr.org/openicpsr/project/100707/version/V22/view?path=/openicpsr/100707/fcr:versions/V22/offenses_known_csv_1960_2024_month.zip&type=file>

---

## Option 2: NIBRS Microdata via ICPSR (Incident-Level with TIME)

**Why this data**: The Administrative Segment contains **incident date AND time (hour)** at the individual incident level - critical for analyzing nighttime vs daytime crime in relation to moonlight.

- **Source**: Jacob Kaplan's Concatenated Files: National Incident-Based Reporting System (NIBRS) Data, 1991-2024
- **Access Link**: <https://www.openicpsr.org/openicpsr/project/118281>
- **Documentation**: <https://ucrbook.com/> (Jacob Kaplan's UCR/NIBRS documentation book)

### Key Segments to Download:

| Segment | File | Purpose |
|---------|------|---------|
| **Administrative** | `administrative_segment_rds_1991_2024.zip` | Contains incident date AND time (hour). CRITICAL for nighttime analysis. |
| **Batch Header** | `batch_header_rds_1991_2024.zip` | Contains ORI codes and agency geographic info (county FIPS, state, population). Needed to link incidents to counties. |
| **Offense** | `offense_segment_rds_1991_2024.zip` | Contains offense type (burglary, robbery, assault, etc.), location type, weapon involved. |
| **Offender** | `offender_segment_rds_1991_2024.zip` | Optional: offender demographics (age, sex, race). |
| **Victim** | `victim_segment_rds_1991_2024.zip` | Optional: victim demographics and injury info. |

### Download Instructions:

1. Go to <https://www.openicpsr.org/openicpsr/project/118281>
2. Create an ICPSR account (free with .edu email) or log in
3. Download the RDS format files (recommended for R users)
4. Place downloaded ZIP files in: `data/alexr_icprsr_crime_data/`
5. Run `notebooks/nibrs_data_exploration.ipynb` to extract and validate the data

### Linking ORI to County:

Each agency is identified by ORI (Originating Agency Identifier) in the Administrative Segment, which can be linked to county FIPS code via the Batch Header Segment.

---

## Other Data Sources

### NASA Black Marble (VNP46A3)
- **Description**: Monthly lunar BRDF-adjusted nighttime radiance
- **Source**: NASA LAADS DAAC

### USNO Moon Illumination
- **Description**: Daily moon fraction illuminated
- **Source**: U.S. Naval Observatory Astronomical Applications API