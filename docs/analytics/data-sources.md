---
title: Data Sources
category: "quick-reference"
description: Every dataset that powers the Egg-n-Bacon Housing platform — transaction records, amenity locations, macro indicators, and more
status: published
date: 2026-06-15
personas:
  - first-time-buyer
  - investor
  - upgrader
readingTime: "5 min read"
technicalLevel: beginner
---

# Data Sources

**Last Updated**: 2026-06-15

This page documents every dataset behind the analysis on this site. All structured data comes from official Singapore government sources.

---

## Property Transactions

| Dataset                          | Source                              | Time Range          | Records      |
| -------------------------------- | ----------------------------------- | ------------------- | ------------ |
| HDB Resale Prices                | data.gov.sg + historical archives   | Jan 1990 – Jun 2026 | ~970,000     |
| HDB Rental Medians               | data.gov.sg                         | Jan 2021 – May 2026 | 200,000+     |
| Private Residential Transactions | URA (Urban Redevelopment Authority) | Quarterly batches   | ~40,000      |
| URA Rental Index                 | data.gov.sg                         | 2004-Q1 – 2026-Q1   | 515 quarters |

HDB resale data spans **36 years** of transactions, making it one of the most comprehensive public housing datasets available anywhere.

---

## Amenity Proximity

Every transaction is enriched with straight-line distance to the nearest amenities.

### Daily Convenience

| Amenity                  | Locations Mapped | Median Distance |
| ------------------------ | ---------------- | --------------- |
| Childcare Centre         | 1,925            | 126 m           |
| Preschool / Kindergarten | 2,290            | 125 m           |
| Supermarket              | 526              | 290 m           |
| MRT Station              | 180+             | 513 m           |
| Hawker Centre            | 129              | 596 m           |
| Park / Nature Reserve    | 450              | 622 m           |
| Shopping Mall            | 112              | —               |

### Health & Lifestyle

| Amenity              | Source               | Notes                                                   |
| -------------------- | -------------------- | ------------------------------------------------------- |
| CHAS Clinics         | data.gov.sg          | Subsidised primary care clinics                         |
| Sports Facilities    | SportSG              | Stadiums, pools, sports halls                           |
| Community Clubs      | People's Association | CC locations island-wide                                |
| Green Mark Buildings | BCA                  | Green-certified buildings (environmental quality proxy) |
| Bus Stops            | LTA                  | Public bus stop locations                               |

Amenity locations are sourced from data.gov.sg. Shopping mall data is from Wikipedia and geocoded via OneMap. Green Mark buildings (3,900+) are geocoded by postal code.

---

## Macro Economic Indicators

| Indicator                  | Frequency | Coverage        | Why It Matters                                              |
| -------------------------- | --------- | --------------- | ----------------------------------------------------------- |
| Consumer Price Index (CPI) | Monthly   | 1961 – Apr 2026 | Tracks inflation — adjusts historical prices for comparison |
| GDP (Chained 2015 Dollars) | Quarterly | 1976 – 2026-Q1  | Economic growth context for price trends                    |
| Unemployment Rate          | Quarterly | 1992 – 2026-Q1  | Labour market health as a price driver                      |
| SORA (Swap Offer Rate)     | Monthly   | 2021 – 2025     | Benchmark mortgage rate — directly affects affordability    |
| SORA 3M (Compounded)       | Monthly   | 2007 – Apr 2026 | 3-month compounded SORA — primary floating-rate benchmark   |
| HDB Resale Price Index     | Quarterly | 1990 – 2026-Q1  | Official HDB price benchmark for model validation           |
| URA Property Price Index   | Quarterly | 1975 – 2026-Q1  | Official private residential price benchmark                |
| Housing Supply Pipeline    | Quarterly | 2014 – 2026-Q1  | Future private housing supply by development stage          |

---

## Block-Level Metadata

| Dataset                  | Records       | Key Features                                                                       |
| ------------------------ | ------------- | ---------------------------------------------------------------------------------- |
| HDB Property Information | 13,289 blocks | Building height, year completed, dwelling units, flat type supply, mixed-use flags |

Every HDB transaction is enriched with its block's physical attributes — providing a granular view of building age, density, and type composition.

---

## Schools

| Dataset                     | Records             | Notes                                          |
| --------------------------- | ------------------- | ---------------------------------------------- |
| MOE School Directory        | 337 schools         | Names, addresses, levels                       |
| School Tier Classifications | Primary + Secondary | Quality tiers for school-zone premium analysis |

Schools are geocoded via OneMap (Singapore's official map service) to compute proximity from each property.

---

## Income & Affordability

| Dataset                              | Source                                   | Coverage                               |
| ------------------------------------ | ---------------------------------------- | -------------------------------------- |
| Income Distribution by Planning Area | General Household Survey 2015 (SingStat) | ~30 planning areas, 15 income brackets |

The platform computes a **weighted median monthly income** per planning area from 15 income brackets — replacing a one-size-fits-all affordability assumption with area-specific income data.

---

## Geocoding & Geography

- **OneMap API** — Singapore's official geospatial service. Used to convert addresses to coordinates for every property, school, shopping mall, and green-certified building.
- **Planning Area Boundaries** — Official polygons from OneMap used to assign each transaction to a planning area.

---

## Data Pipeline

Raw data flows through four quality layers before reaching this website:

| Layer        | What Happens                                                                                 |
| ------------ | -------------------------------------------------------------------------------------------- |
| **Bronze**   | Raw data ingested from APIs and manual files                                                 |
| **Silver**   | Validated, cleaned, deduplicated                                                             |
| **Gold**     | Enriched with amenity distances, macro indicators, school tiers, block metadata, income data |
| **Platinum** | Unified dataset, metrics, and dashboard exports                                              |

The final unified dataset contains over **1 million transactions** across **120+ feature columns**, covering **12 amenity proximity types** and **8 macro economic indicators**.
