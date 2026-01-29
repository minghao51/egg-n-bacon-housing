# Property Type & MRT Impact - Quick Summary

**Question**: Does property type (HDB, Condo, EC) influence MRT impact on prices?

---

## Short Answer: **Cannot Compare - Data Missing**

**Critical Finding**: Amenity features (MRT distances) are **ONLY available for HDB** in the current dataset.

| Property Type | Records with MRT Data | Records without MRT Data |
|---------------|----------------------|-------------------------|
| **HDB** | **97,133 (100%)** | 0 |
| **Condominium** | 0 (0%) | **109,576** |
| **EC** | 0 (0%) | **16,826** |

---

## What We CAN Analyze: Heterogeneous Effects WITHIN HDB

Within HDB properties, MRT impact varies dramatically by sub-group:

### 1. By Flat Type (Unit Size)

| Flat Type | MRT Premium* | Sensitivity |
|-----------|--------------|-------------|
| 2 ROOM | **$4.24/100m** | **4.1x** (highest) |
| 3 ROOM | **$3.96/100m** | **3.8x** |
| 5 ROOM | **$2.35/100m** | **2.3x** |
| 4 ROOM | **$1.79/100m** | **1.7x** |
| EXECUTIVE | **$1.04/100m** | **1.0x** (baseline) |

*Negative value = price decreases as you move away from MRT

**Interpretation**: Smaller HDB units value MRT access **4x more** than large units.

**Why?**
- 2 ROOM owners: Budget buyers, transit-dependent
- EXECUTIVE owners: Higher income, likely car owners

---

### 2. By Location (Town)

**Massive variation**: **$97.73 range** across towns

| Town | MRT Premium | Interpretation |
|------|-------------|----------------|
| **CENTRAL AREA** | **+$59.19/100m** | MRT proximity = HUGE premium |
| **SERANGOON** | **+$12.91/100m** | Strong positive effect |
| Most towns | ~$0/100m | Minimal effect |
| **MARINE PARADE** | **-$38.54/100m** | MRT proximity = DISCOUNT |

**Stunning Facts**:
- Central Area: Closer to MRT = **Higher price** (opposite of most areas)
- Marine Parade: Closer to MRT = **Lower price** (ocean views matter more)
- **100x variation** across towns!

---

### 3. By Price Tier

| Tier | Price Range | MRT Premium |
|------|-------------|-------------|
| **Premium** | $599-1500 | **+$6.03/100m** |
| Mid-Premium | $525-599 | -$0.35/100m |
| Mid-Budget | $465-525 | -$0.28/100m |
| **Budget** | $249-465 | **-$0.73/100m** |

**Counterintuitive**: Premium HDB shows **positive** MRT effect, budget shows **negative**.

**Why?** Possibly:
- Premium HDB in central areas (MRT valuable)
- Budget HDB in suburbs (MRT less relevant)

---

## Why No Condo/EC Data?

### Likely Reason: Pipeline Limitation

The amenity distance calculation (L2 pipeline) probably only processes:
- HDB resale transactions (with BLK + ROAD_NAME)
- Not private condo/EC transactions

### To Add Condo/EC Data:

**Option 1**: Extend L2 pipeline
```python
# In scripts/pipeline/L2_rental.py or similar
# Calculate distances from condo lat/lon to MRT stations
```

**Option 2**: Quick hack for analysis
```python
# Load condo coordinates
condo_geo = pd.read_parquet('data/pipeline/L2/housing_unique_searched.parquet')
condo_geo = condo_geo[condo_geo['property_type'] == 'private']

# Load MRT station locations
mrt_stations = gpd.read_file('data/manual/csv/datagov/MRTStations.geojson')

# Calculate distances
from scipy.spatial import cKDTree
# ... distance calculation logic
```

---

## Expected Results for Condo vs EC (Hypothesis)

If we had the data, I'd expect:

| Property Type | Expected MRT Sensitivity | Rationale |
|---------------|-------------------------|-----------|
| **HDB** | **High** (observed: $1-4/100m) | Public transit dependent |
| **EC** | **Medium** | Hybrid (HDB buyers upgrading) |
| **Condo** | **Low** | Higher car ownership rates |

**Testable Predictions**:
1. Condo MRT premium < HDB MRT premium
2. EC MRT premium ≈ HDB (similar buyer demographics)
3. Luxury condos: Zero or negative MRT effect

---

## Bottom Line

1. **Current analysis**: HDB-only (97K records)
2. **Cannot compare**: Property types without amenity data
3. **Key insight**: Within HDB, MRT impact varies **4x to 100x** by sub-group
4. **Action needed**: Calculate amenity distances for Condo/EC to compare

---

## Next Steps

Would you like me to:
1. **Extend the L2 pipeline** to calculate MRT distances for condos/EC?
2. **Quick analysis** using existing condo coordinates (hack solution)?
3. **Research** why amenity features weren't calculated for private properties?
4. **Something else**?

Let me know how you'd like to proceed!
