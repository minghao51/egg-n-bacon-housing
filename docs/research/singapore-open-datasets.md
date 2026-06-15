# Singapore Open Datasets for Housing Price Analytics

Comprehensive catalog of government open datasets useful for housing price analysis.
Sourced from **data.gov.sg** (4,410 total datasets scanned via `api-production.data.gov.sg/v2/public/api/datasets`).

## API Access

All datasets use the same base API:

```
https://data.gov.sg/api/action/datastore_search?resource_id={datasetId}
```

**Authentication:** Optional API key via `x-api-key` header (request at data.gov.sg dashboard).
**Rate limits:** Higher with API key. Pagination via `_links.next` in response.
**Full listing API:** `GET https://api-production.data.gov.sg/v2/public/api/datasets?page={n}`

---

## 1. HDB Housing & Resale (Housing & Development Board)

### Already In Use

| Dataset                                | Resource ID                          | Status          |
| -------------------------------------- | ------------------------------------ | --------------- |
| HDB Resale Flat Prices (Jan 2017+)     | `d_8b84c4ee58e3cfc0ece0d773c8ca6abc` | **In pipeline** |
| Resale Flat Prices (Jan 2015–Dec 2016) | `d_ea9ed51da2787afaf8e51f827c304208` | Available       |
| Resale Flat Prices (Mar 2012–Dec 2014) | `d_2d5ff9ea31397b66239f245f57751537` | Available       |

### New — High Value

| Dataset                                                     | Resource ID                          | Format  | Notes                                                                     |
| ----------------------------------------------------------- | ------------------------------------ | ------- | ------------------------------------------------------------------------- |
| HDB Resale Price Index (1Q2009=100), Quarterly              | `d_14f63e595975691e7c24a27ae4c07c79` | CSV     | Macro indicator for price trends                                          |
| HDB Property Information                                    | `d_17f5382f26140b1fdae0ba2ef6239d2f` | CSV     | All HDB blocks: address, flat types, year completed, total dwelling units |
| Dwelling Units under HDB's Management by Town/Flat Type     | `d_07b1eeeb22efdf7faf5bd6a13667359d` | CSV     | Supply by town                                                            |
| HDB Households by Flat Type                                 | `d_db69c88a1ff684356b8b38dc0e9b432c` | CSV     | Household composition                                                     |
| Price Range of HDB Flats Offered                            | `d_2d493bdcc1d9a44828b6e71cb095b88d` | CSV     | BTO pricing reference                                                     |
| Applications for HDB Loan Eligibility Letters               | `d_38ec7e5cd735d597ab85765d2ef1a39b` | CSV     | Demand indicator                                                          |
| Applications for Resale/Rental Flats                        | `d_c47771d51ac7d86ac300835b27848ff0` | CSV     | Demand indicator                                                          |
| Number of Sold and Rented HDB Residential Units             | `d_67966e5fd5dce14cf9fa5f0bc5164faf` | CSV     | Supply allocation                                                         |
| Completion Status of HDB Residential Developments           | `d_582672d2f972194786d01efe151892b7` | CSV     | BTO completion tracking                                                   |
| Completion Status of HDB Residential Units by Town/Estate   | `d_9bbcd0c9b0351c7f41c9bfdcdc746668` | CSV     | Town-level supply pipeline                                                |
| Cumulative HDB Commercial Properties Completed Since 1960   | `d_007b79018e47094e8cd62bf6f6d9ed8e` | CSV     | Mixed-use indicator                                                       |
| HDB Branches (GEOJSON)                                      | `d_3535361f967e8005dc44b4ce4d2c5276` | GEOJSON | Branch locations                                                          |
| HDB Car Parks Outlines (GEOJSON)                            | `d_7e8ecc485c30c0f22eb323f02b9075f1` | GEOJSON | Parking proximity                                                         |
| HDB Cycling Paths Under-Construction (GEOJSON)              | `d_9e363d0eb7910dc7f53c44e4fe654586` | GEOJSON | Future connectivity                                                       |
| HDB Lift Upgrading Programme (GEOJSON)                      | `d_9b5886a025c8db1192a8fada42bd4330` | GEOJSON | Upgrading indicator                                                       |
| HDB Neighbourhood Renewal Programme (GEOJSON)               | `d_156a38dc024d2b20a6c1d0c0179e797c` | GEOJSON | Estate improvement                                                        |
| HDB Roads Under Construction (GEOJSON)                      | `d_157d034c579e12a095c967ca2a463d01` | GEOJSON | Infrastructure pipeline                                                   |
| Median Annual Value and Property Tax by Type of HDB         | `d_48143be392f1ed22f0700835212e5a60` | CSV     | IRAS — tax assessment values                                              |
| HDB Resident Population by Geographical Distribution        | `d_0a6c6d71f6fa14e2d27e406f1d018439` | CSV     | Population by town/estate                                                 |
| Average/Median Age of HDB Population by Ethnic Group        | `d_a24664d0ad7d21edfc7245e0195d7503` | CSV     | Demographics                                                              |
| HDB Elderly/Future Elderly Resident Population by Flat Type | `d_6c678a9e6cf49086c1fea012c40ceafe` | CSV     | Aging demographics                                                        |
| Applications for HDB Mortgage (Bank Loan)                   | `d_fbb057402a1d4a953a9b46babbdbf1fc` | CSV     | Demand + mortgage indicator                                               |

---

## 2. Private Property & Real Estate (URA)

### Already In Use

| Dataset                                   | Resource ID                          | Status          |
| ----------------------------------------- | ------------------------------------ | --------------- |
| Private Residential Property Rental Index | `d_8e4c50283fb7052a391dfb746a05c853` | **In pipeline** |

### New — High Value

| Dataset                                                                        | Resource ID                          | Format | Notes                          |
| ------------------------------------------------------------------------------ | ------------------------------------ | ------ | ------------------------------ |
| Private Residential Property Price Index (Base Q2009-Q1=100), Quarterly        | `d_97f8a2e995022d311c6c68cfda6d034c` | CSV    | Core macro price indicator     |
| Private Residential Property Price Index By Type of Property                   | `d_c0c26484c655113b0ab5abaa0a49952b` | CSV    | By detached/semi/terrace/condo |
| Private Residential Property Price Index (Base Q2009-Q1=100)                   | `d_f76411aa34d98559b6194419d796ce59` | CSV    | Alternative index version      |
| Commercial Rental Index (Base Q1998-Q4=100), Quarterly                         | `d_862c74b13138382b9f0c50c68d436b95` | CSV    | Commercial context             |
| Private Residential Transactions — Core Central Region, Quarterly              | `d_c287c8be114bfa7d055b27ab2c87de83` | CSV    | CCR volume                     |
| Private Residential Transactions — Rest of Central Region, Quarterly           | `d_5785799d63a9da091f4e0b456291eeb8` | CSV    | RCR volume                     |
| Private Residential Transactions — Outside Central Region, Quarterly           | `d_1a7823f3d31e7db4b426833833762bab` | CSV    | OCR volume                     |
| Private Residential Transactions — Whole of Singapore, Quarterly               | `d_7c69c943d5f0d89d6a9a773d2b51f337` | CSV    | Total volume                   |
| Supply of Private Residential Properties in Pipeline by Status, Quarterly      | `d_baa848bbdbf4af7b4d709f147fcf3c9b` | CSV    | **Supply pipeline**            |
| Supply of Private Residential Properties in Pipeline by Status, Annually       | `d_7a882bd3d44374a7f701fc6a07620bf8` | CSV    | Annual supply pipeline         |
| Uncompleted Private Residential Units Launched by Market Segment, Quarterly    | `d_70824d34defde87d88faccc5d5b1c6ea` | CSV    | New launches                   |
| Uncompleted Private Residential Units Sold by Market Segment, Quarterly        | `d_e1c5b0df62729e69c82716355ef295ba` | CSV    | Under-construction sales       |
| Unsold Private Residential Units with Planning Approvals by Segment, Quarterly | `d_84d05d45049108f0fd2e99b66bd19cfe` | CSV    | Oversupply indicator           |
| Completed Private Residential Units Sold in the Quarter, Quarterly             | `d_a283de8cb3b4e80a228bf5f5e0bc4449` | CSV    | Completed sales                |
| Approval, Construction & Completion of Private Residential Properties, Annual  | `d_38ed343cc32c3e0b6ebc43a6058e9860` | CSV    | Development lifecycle          |
| Executive Condominium Units Launched & Sold, Quarterly                         | `d_19c79027c2e6be3c39d637151bd2188d` | CSV    | EC market                      |
| Sale Position of ECs with Pre-Requisites for Sale, Quarterly                   | `d_8b71bc3e1386261039d7ad95efdc3328` | CSV    | EC supply position             |
| Supply of ECs in Pipeline by Development Status, Quarterly                     | `d_4e8073b6cf272998f14fd970a24c1639` | CSV    | EC supply pipeline             |
| Rental Indices of Non-Landed Private Residential Properties By Locality        | `d_56b0c7f6538be69f24956634d88d82e8` | CSV    | SingStat rental by locality    |
| Conservation Sites Sold By URA                                                 | `d_1eefe4d027b4d59437321f25e00be9e7` | CSV    | URA conservation land sales    |
| Registration of Documents Lodged for HDB Properties                            | `d_88e252fe9febb6cf122a24f9193f1138` | CSV    | SLA — caveat/instrument counts |
| CEA Salesperson Information                                                    | `d_07c63be0f37e6e59c07a4ddc2fd87fcb` | CSV    | Real estate agent directory    |

---

## 3. URA Master Plan & Land Use (Urban Redevelopment Authority)

### Core Layers (Latest — Master Plan 2025)

| Dataset                                              | Resource ID                          | Format  | Notes                                     |
| ---------------------------------------------------- | ------------------------------------ | ------- | ----------------------------------------- |
| **Master Plan 2025 Land Use Layer**                  | `d_a8c3546b26712e35021f3a681d0353ae` | GEOJSON | **Gazetted 1 Dec 2025** — land use zoning |
| Master Plan 2025 Rail Line Layer                     | `d_1c6365f0cad13a77bd79bdbb499131bf` | GEOJSON | Future rail network                       |
| Master Plan 2025 Rail Station Layer                  | `d_2c06c9fe8ae724b5d33efa1f203e2c38` | GEOJSON | Future station locations                  |
| Master Plan 2025 Rail Station Name Layer             | `d_449ee0cec1f9574f8f34712da6f7456f` | GEOJSON | Station names                             |
| Master Plan 2025 SDCP Cycling Network layer          | `d_8fd4e04e7058ee19521d123caf28a855` | GEOJSON | Planned cycling infrastructure            |
| Master Plan 2025 SDCP Integrated Transport Hub layer | `d_a5047ce23e02c5ca3aa56199d7d3eb59` | GEOJSON | ITH locations                             |
| Master Plan 2025 SDCP Building Height Control layer  | `d_0720d955bce304046d173d9e2a309652` | GEOJSON | Height restrictions                       |
| Master Plan 2025 SDCP Urban Design Area layer        | `d_e0ddeb937ca4448bf8d0ca203c35271b` | GEOJSON | Design guidelines                         |
| Master Plan 2025 SDCP Urban Design Corridor layer    | `d_a0ccf1ee244315b08056590bbc89e587` | GEOJSON | Corridor guidelines                       |
| Master Plan 2025 SDCP Street Block layer             | `d_386e331f79c9fb331f32081fc5647439` | GEOJSON | Street block design                       |
| Master Plan 2025 SDCP UNESCO Heritage Site layer     | `d_7a36470accc937bd7752ba6f829b74c1` | GEOJSON | Heritage protection                       |
| Master Plan 2025 SDCP Park Text layer                | `d_3cd4a73c99d431a831f1008642ddef41` | GEOJSON | Park annotations                          |
| Master Plan 2025 SDCP Park Connector Line layer      | `d_cebde179d5cd6b85be36d618c8fe3b85` | GEOJSON | Park connectors                           |

### Master Plan 2019 Layers

| Dataset                                                        | Resource ID                          | Format  | Notes                     |
| -------------------------------------------------------------- | ------------------------------------ | ------- | ------------------------- |
| Master Plan 2019 Land Use layer                                | `d_90d86daa5bfaa371668b84fa5f01424f` | GEOJSON | Previous land use zoning  |
| Master Plan 2019 Building layer                                | `d_e8e3249d4433845bdd8034ae44329d9e` | GEOJSON | Building footprints       |
| Master Plan 2019 Rail Line layer                               | `d_222bfc84eb86c7c11994d02f8939da8d` | GEOJSON | Rail network              |
| Master Plan 2019 Rail Station layer                            | `d_8d886e3a83934d744acdf5bc6959999`  | GEOJSON | Station locations         |
| Master Plan 2019 SDCP Landed Housing Area Text                 | `d_5bb472b597121183747651ec6b56b583` | GEOJSON | Landed housing zones      |
| Master Plan 2019 SDCP Landed Housing Area Leader Line          | `d_e9e9ba577d5b2d359cd1cc3abbac3388` | GEOJSON | Landed housing boundaries |
| Master Plan 2019 SDCP Cycling Path layer                       | `d_9326f791b521187f503149712fc400ef` | GEOJSON | Cycling infrastructure    |
| Master Plan 2019 SDCP Integrated Transport Hub layer           | `d_3ebc4424254906fb51e6b34916df10a9` | GEOJSON | ITH locations             |
| Master Plan 2019 Symbol Line layer (GPR, Nature, Conservation) | `d_fe6db1a882ca2ceddb208d1ab6c7d874` | GEOJSON | Planning control lines    |
| Master Plan 2019 Symbol Text layer                             | `d_dc4918b82cb79cbb706c8f35bc412242` | GEOJSON | Annotations               |

### Planning Boundaries (All MP Versions)

| Dataset                                              | Resource ID                          | Format  | Notes                      |
| ---------------------------------------------------- | ------------------------------------ | ------- | -------------------------- |
| **Master Plan 2019 Planning Area Boundary (No Sea)** | `d_4765db0e87b9c86336792efe8a1f7a66` | GEOJSON | **Planning area polygons** |
| **Master Plan 2019 Subzone Boundary (No Sea)**       | `d_8594ae9ff96d0c708bc2af633048edfb` | GEOJSON | **Subzone polygons**       |
| Master Plan 2019 Region Boundary (No Sea)            | `d_db9b98d7b681a83009baab639605a1ba` | GEOJSON | Region polygons            |
| Master Plan 2014 Planning Area Boundary (No Sea)     | `d_28feff20a3500b31589c8adb057b7199` | GEOJSON | Historical                 |
| Master Plan 2014 Subzone Boundary (No Sea)           | `d_226cacceceff94f0c8b814962a5307c9` | GEOJSON | Historical                 |
| Master Plan 2008 Planning Area Boundary (No Sea)     | `d_773f010a4eaae0ce6d81cbe78d251642` | GEOJSON | Historical                 |
| Master Plan 2008 Subzone Boundary (No Sea)           | `d_c50f318157e6f327c639ad6b18a7bd63` | GEOJSON | Historical                 |
| Master Plan 1998 Planning Area Boundary (No Sea)     | `d_448eb9464bde22a85d6e9efff8489906` | GEOJSON | Historical                 |

### Parks & Waterbodies

| Dataset                                         | Resource ID                          | Format  | Notes                 |
| ----------------------------------------------- | ------------------------------------ | ------- | --------------------- |
| Master Plan 2019 SDCP Park and Open Space layer | `d_9ec9fe2ff2c6c520dd8679933a4a059a` | GEOJSON | Park zones            |
| Master Plan 2019 SDCP Waterbody layer           | `d_0b0792ae30cd6cce62e5ea55fc37860e` | GEOJSON | Water bodies          |
| Master Plan 2019 SDCP Park Connector Line layer | `d_3e902a9be74243ad68998e66b7dd4970` | GEOJSON | Park connectors       |
| SDCP Park                                       | `d_b643136cce510c4157fcf70796be1bde` | GEOJSON | Current park polygons |
| SDCP Park Connector                             | `d_5b2de205d2b800dbe4f5fa8a80dc37e1` | GEOJSON | Current connectors    |

### Hexagonal Grids (for spatial aggregation)

| Dataset                        | Resource ID                          | Format  | Notes         |
| ------------------------------ | ------------------------------------ | ------- | ------------- |
| Hexagonal grids of radius 40m  | `d_fb816f574a53c0b6e945a74c74271cf6` | GEOJSON | Fine-grained  |
| Hexagonal grids of radius 100m | `d_e675592504191d21e0b8687981bb3fe7` | GEOJSON | Standard      |
| Hexagonal grids of radius 200m | `d_3c0dc686af45c42cddce3b70777a0ce7` | GEOJSON | Standard      |
| Hexagonal grids of radius 300m | `d_d31528e9725c0e4bffa62ae51ff75a11` | GEOJSON | Medium        |
| Hexagonal grids of radius 500m | `d_c087309e1cec43d7547adf4b98dd0c75` | GEOJSON | MRT catchment |

### Parking

| Dataset                                  | Resource ID                          | Format  | Notes                 |
| ---------------------------------------- | ------------------------------------ | ------- | --------------------- |
| Capacity of URA Parking Places (GEOJSON) | `d_9bf8620ecfdc8a5f8f77e3f02160af5c` | GEOJSON | URA parking capacity  |
| URA Parking Lot (GEOJSON)                | `d_d959102fa76d58f2de276bfbb7e8f68e` | GEOJSON | URA parking locations |

---

## 4. Transport — LTA DataMall on data.gov.sg

### Bus

| Dataset                                             | Resource ID                          | Format  | Notes                                |
| --------------------------------------------------- | ------------------------------------ | ------- | ------------------------------------ |
| **LTA Bus Stop**                                    | `d_3f172c6feb3f4f92a2f47d93eed2908a` | GEOJSON | **All bus stop locations**           |
| Bus Stop Chinese Names                              | `d_54592963dbd23464b875379a21c2cfe9` | CSV     | Chinese bus stop names               |
| Public Transport Capacity — Bus Routes in Operation | `d_4b650f7d8233247fc1a2d6bb974df260` | CSV     | Bus route metrics                    |
| Wheelchair Accessible Bus Services                  | `d_93a8f9b3a463fc491b25d9a49f1dc654` | CSV     | Accessibility                        |
| Premium Bus Services                                | `d_be2accb464cc5600de937eb9000a0255` | CSV     | Premium routes                       |
| Annual Bus Population by Passenger Capacity         | `d_6877490600b1cc6c4dba2f692b8ddabb` | CSV     | Fleet metrics                        |
| Fares for Express/Feeder/Trunk Bus Services         | various                              | CSV     | Public Transport Council fare tables |

### MRT / LRT / Rail

| Dataset                            | Resource ID                          | Format  | Notes                    |
| ---------------------------------- | ------------------------------------ | ------- | ------------------------ |
| **LTA MRT Station Exit (GEOJSON)** | `d_b39d3a0871985372d7e1637193335da5` | GEOJSON | **MRT station exits**    |
| Train Station Chinese Names        | `d_d312a5b127e1ae74299b8ae664cedd4e` | CSV     | Chinese station names    |
| Number of MRT and LRT Stations     | `d_34dc2eb007a14ef406474abfb43c8671` | CSV     | Station counts over time |
| Rail Length (km) At End-of-Year    | `d_d6e505b87580a4bae4aae0beb07d3de6` | CSV     | Network expansion        |
| SDCP MRT Station Point             | `d_210d2b691cec8a10dcdbd35c7ce26efd` | GEOJSON | MRT station points       |

### Cycling & Active Mobility

| Dataset                            | Resource ID                          | Format  | Notes                         |
| ---------------------------------- | ------------------------------------ | ------- | ----------------------------- |
| **Cycling Path Network (GEOJSON)** | `d_8f468b25193f64be8a16fa7d8f60f553` | GEOJSON | **Island-wide cycling paths** |
| LTA Bicycle Rack (GEOJSON)         | `d_937424cca6d1617288a82a7aeb89f76d` | GEOJSON | Bicycle parking               |

### Road Infrastructure

| Dataset                              | Resource ID                          | Format  | Notes                |
| ------------------------------------ | ------------------------------------ | ------- | -------------------- |
| Master Plan 2019 Road Name layer     | `d_93f8f9b3a463fc491b25d9a49f1dc654` | GEOJSON | Road names           |
| Master Plan 2019 Road Graphic layer  | `d_95a29fbb10cf94a3c263d33861d7b6c6` | GEOJSON | Road graphics        |
| Length of Roads (Lane-Kilometres)    | `d_8415afe86e594bdc18f0f04a71d5f210` | CSV     | Road network length  |
| Public Roads (End Of Period), Annual | `d_f73d13943f7a3cc1aca76b18fea75013` | CSV     | Road inventory       |
| LTA Gantry (GEOJSON)                 | `d_753090823cc9920ac41efaa6530c5893` | GEOJSON | ERP gantries         |
| LTA School Zone (GEOJSON)            | `d_abf023b38d9bc451484e3d67b562bc5c` | GEOJSON | School zones         |
| LTA Silver Zone (GEOJSON)            | `d_dc343c021aa470fc71da90d31e552a9a` | GEOJSON | Elderly safety zones |

### Public Transport Metrics

| Dataset                                                           | Resource ID                          | Format | Notes               |
| ----------------------------------------------------------------- | ------------------------------------ | ------ | ------------------- |
| Public Transport Utilisation — Average Public Transport Ridership | `d_75248cf2fbf340de6a746dc91ec9223c` | CSV    | Ridership trends    |
| Public Transport Utilisation — Average Trip Distance              | `d_1e8c9a3f599bca92c76bdb7d8a52a79a` | CSV    | Trip length         |
| Public Transport Capacity — Average Daily Distance Travelled      | `d_120bba76c28dd4706e0cf85693827e64` | CSV    | Capacity metric     |
| Public Transport Journeys                                         | `d_d6921f812624c2b1bb1d68269354dc71` | CSV    | Journey counts      |
| Public Transport Capacity — Monthly Taxi Population               | `d_884c2efb2103bc66dc2b8725173be85b` | CSV    | Taxi fleet size     |
| Average Daily Traffic Volume Entering the City                    | `d_3136f317a1f282a33fe7a2f6a907c047` | CSV    | City traffic volume |
| Average Annual Kilometres Travelled Per Vehicle                   | `d_bdc4c6434e47b055de4b5f2fde10c1af` | CSV    | Vehicle usage       |
| Annual Motor Vehicle Population by VQS Categories                 | `d_cc30f50369bcd6b6f848a586bded2290` | CSV    | Vehicle types       |

### Car Parking

| Dataset                    | Resource ID                          | Format | Notes                     |
| -------------------------- | ------------------------------------ | ------ | ------------------------- |
| Carpark Rates              | `d_9f6056bdb6b1dfba57f063593e4f34ae` | CSV    | Parking rates (2018)      |
| JTC Carpark Information    | `d_3b0c377cde41041c93f893d0a92e9fe7` | CSV    | JTC carpark data          |
| Carpark Availability (HDB) | `d_ca933a644e55d34fe21f28b8052fac63` | API    | **Real-time HDB carpark** |

### Real-Time APIs (LTA DataMall)

| Dataset               | Resource ID                          | Format | Notes                     |
| --------------------- | ------------------------------------ | ------ | ------------------------- |
| Taxi Availability     | `d_e25662f1a062dd046453926aa284ba64` | API    | Real-time taxi locations  |
| Traffic Images        | `d_6cdb6b405b25aaaacbaf7689bcc6fae0` | API    | Real-time traffic cameras |
| Traffic Facilities    | `d_046cd30aebfcb866dcb6fbf2fd4d91fb` | CSV    | Traffic infrastructure    |
| Pedestrian Facilities | `d_45175a1ff46644414a9a1aeef564e6f`  | CSV    | Pedestrian infrastructure |
| Traffic Lights        | `d_03c133a999057087ebc3a783fba5bfa8` | CSV    | Signal locations          |

---

## 5. NEA Environmental Datasets

### Real-Time APIs

| Dataset                             | Resource ID                           | Format | Notes                     |
| ----------------------------------- | ------------------------------------- | ------ | ------------------------- |
| **PSI (Pollutant Standards Index)** | `d_fe37906a0182569d891506e815e819b7`  | API    | **Real-time air quality** |
| **PM2.5**                           | `d_e1058d6974c877257e32048ab128ad83`  | API    | **Real-time PM2.5**       |
| Rainfall across Singapore           | `d_6580738cdd7db79374ed3152159fbd69`  | API    | Real-time rainfall        |
| Air Temperature across Singapore    | `d_66b77726bbae1b33f218db60ff5861f0`  | API    | Real-time temperature     |
| Wind Speed across Singapore         | `d_7677738484067741bf3b56ab5d69c7e9`  | API    | Real-time wind            |
| Wind Direction across Singapore     | `d_534cf203023b51f51f879145ccc56ff9`  | API    | Real-time wind direction  |
| Relative Humidity across Singapore  | `d_2d3b0c4da1289a9a59efca806441e1429` | API    | Real-time humidity        |
| Ultraviolet Index (UVI)             | `d_1b676cd174a9af4704fdb3f9aa58ff5e`  | API    | Real-time UV              |
| 2-hour Weather Forecast             | `d_3f9e064e25005b0e42969944ccaf2e7a`  | API    | Short-range forecast      |
| 24-hour Weather Forecast            | `d_ce2eb1e307bda31993c533285834ef2b`  | API    | Medium-range forecast     |
| 4-day Weather Forecast              | `d_f131f6e343bf8168e4057a04c4326a0a`  | API    | Extended forecast         |
| Lightning Observation               | `d_08238953fe0f6dd13f10714ebfbcb9f9`  | API    | Lightning detection       |
| Wet Bulb Globe Temperature (WBGT)   | `d_87884af1f85d702d4f74c6af13b4853d`  | API    | Heat stress index         |
| Wet Bulb Temperature — Hourly       | `d_f222c70a7c00c5a5a9d4ec432d67f6e8`  | CSV    | Hourly readings           |

### Historical Data (CSV downloads)

| Dataset                                     | Resource ID                          | Format | Coverage           |
| ------------------------------------------- | ------------------------------------ | ------ | ------------------ |
| Historical Rainfall across Singapore (2024) | `d_a0b69d3e02576a1fd0ab673e71f83507` | CSV    | 2024               |
| Historical Air Temperature (2024)           | `d_910c81fce47f38574015b3882ac59254` | CSV    | 2024               |
| Historical Wind Speed (2024)                | `d_33f6c1091f73c1451c3aedc4f0061c9c` | CSV    | 2024               |
| Historical Wind Direction (2024)            | `d_c2083cf3e40ddf633b1421ad719067ff` | CSV    | 2024               |
| Historical Relative Humidity (2024)         | `d_7916c4c0cbe0dfaadaeac4b56d732a2a` | CSV    | 2024               |
| Historical 1-hr PM2.5                       | `d_6c0d5fc34838b12472475fdb73c0af29` | CSV    | Multi-year         |
| Historical 24-hr PSI                        | `d_b4cf557f8750260d229c49fd768e11ed` | CSV    | Multi-year         |
| Historical Daily Weather Records            | `d_03bb2eb67ad645d0188342fa74ad7066` | CSV    | Comprehensive      |
| Rainfall — Monthly Total                    | `d_b16d06b83473fdfcc92ed9d37b66ba58` | CSV    | Monthly aggregates |
| Rainfall — Monthly Number of Rain Days      | `d_134857f63c76d227b6fa045f31ce59c1` | CSV    | Rain frequency     |
| Surface Air Temperature — Monthly Mean      | `d_755290a24afe70c8f9e8bcbf9f251573` | CSV    | Monthly mean temp  |
| Air Pollutant — Particulate Matter PM2.5    | `d_397fe8de643aea9927bdee32e49307ff` | CSV    | Annual PM2.5       |
| Air Pollution Levels, Annual                | `d_8f5fa022cbda68494fa70e788600505b` | CSV    | Annual summary     |
| Air Quality, Annual                         | `d_b733fb074ed97f4d322525467b0fa457` | CSV    | DOS annual         |
| Sunshine Duration — Monthly Mean Daily      | `d_9a80d732aa5de0a68be0557fc9437ad0` | CSV    | Sunshine hours     |

### Flood Risk

| Dataset                           | Resource ID                          | Format | Notes                            |
| --------------------------------- | ------------------------------------ | ------ | -------------------------------- |
| **Flood Prone Areas**             | `d_c4aed98f1533eb3a66f65dbb1a30da46` | CSV    | **PUB flood-prone locations**    |
| **Flood Alerts across Singapore** | `d_f1404e08587ce555b9ea3f565e2eb9a3` | API    | **Real-time flood alerts (PUB)** |
| **PUB Water Level Sensors**       | `d_31333fa5cf0834f012d840365b336610` | XLSX   | Drainage water levels            |

### Climate & Emissions

| Dataset                              | Resource ID                          | Format | Notes             |
| ------------------------------------ | ------------------------------------ | ------ | ----------------- |
| Carbon Dioxide Emissions             | `d_4ab7c63c152147042394397f2b61b96a` | CSV    | NEA CO2           |
| Greenhouse Gas Emissions By Gas Type | `d_3be7aef7d4ea78f597bf9f5e90b58dd4` | CSV    | Annual GHG        |
| Greenhouse Gas Emissions By Sector   | `d_1b8dcef6bf32ece26deca60e59d99f71` | CSV    | Sectoral GHG      |
| Recycling Rate By Waste Type         | `d_9740df787da2b59a0b5bd76a6c33453d` | CSV    | Recycling metrics |

---

## 6. BCA Green Mark Buildings

| Dataset                            | Resource ID                          | Format  | Notes                                  |
| ---------------------------------- | ------------------------------------ | ------- | -------------------------------------- |
| **Green Mark Buildings (GEOJSON)** | `d_da116ef216e3fb501846e1c9faf7e683` | GEOJSON | **Spatial — Green Mark with award**    |
| **Green Mark Buildings (CSV)**     | `d_c4bd082b48fa7611713f39e23d250c27` | CSV     | **Certification rating, date, expiry** |

---

## 7. Demographics & Population (SingStat / DOS)

### Core Population

| Dataset                                                              | Resource ID                          | Format | Notes                     |
| -------------------------------------------------------------------- | ------------------------------------ | ------ | ------------------------- |
| **Total Population By Broad Age Group And Sex, At End June, Annual** | `d_6c26f6181f2e5dd62bf3210fa1029074` | CSV    | **Core population data**  |
| Indicators On Population, Annual                                     | `d_3d227e5d9fdec73f3bcadce671c333a6` | CSV    | Key population indicators |
| Births And Fertility Rates, Annual                                   | `d_e39eeaeadb571c0d0725ef1eec48d166` | CSV    | Birth/fertility trends    |
| Key Indicators On The Elderly, Annual                                | `d_dd380a87c84d7bf73e1ca050b176370f` | CSV    | Aging population metrics  |
| Marriages By Residential Status, Annual                              | `d_91317ce93ed54603c1b12f099b57f19b` | CSV    | Marriage trends           |
| Deaths By Broad Groups Of Causes, Annual                             | `d_ecefa3e30b4243c2757678a5f453b24b` | CSV    | Mortality data            |

### Census 2020 (Latest)

| Dataset                                                                                             | Resource ID                          | Format | Notes                            |
| --------------------------------------------------------------------------------------------------- | ------------------------------------ | ------ | -------------------------------- |
| Resident Households by Household Structure, Household Size (Census 2020)                            | `d_5878c7d334eb84983a765d91bd270d7c` | CSV    | Household composition            |
| Resident Households by Type of Dwelling, Household Size and Tenancy (Census 2020)                   | (in filtered set)                    | CSV    | **Dwelling ↔ household**        |
| Employed Residents by Planning Area of Residence and Travelling Time to Work (Census 2020)          | `d_9ebad44ae5f9dff4ccc577a59ac4b208` | CSV    | **Commute patterns by area**     |
| Employed Residents by Planning Area of Workplace and Occupation (Census 2020)                       | `d_a9c214d2534f2da9587ae3bb481f3b85` | CSV    | **Workplace-based demographics** |
| Employed Residents by Planning Area of Workplace, Age Group and Sex (Census 2020)                   | `d_22063c84778e6535b92b4d8f93fd2525` | CSV    | Age profile by workplace area    |
| Employed Residents by Planning Area of Workplace, Usual Mode of Transport (Census 2020)             | `d_f6ddbf6228d561454e27dd158846c688` | CSV    | Transport mode by area           |
| Resident Students by Planning Area of Residence and Usual Mode of Transport to School (Census 2020) | `d_9eaccc6cc0f257cfd74d5c1ceb0fb663` | CSV    | Student transport by area        |

### Income & Expenditure

| Dataset                                                                                         | Resource ID                          | Format | Notes                          |
| ----------------------------------------------------------------------------------------------- | ------------------------------------ | ------ | ------------------------------ |
| Resident Working Persons by Planning Area and Gross Monthly Income (GHS 2015)                   | `d_bb771c5189ce18007621533dd36142bb` | CSV    | **Income by planning area**    |
| Employed Residents by Usual Mode of Transport, Monthly Household Income (Census 2020)           | `d_3c51b2e39181d7b5f0ec3f67a5928681` | CSV    | Income ↔ transport            |
| Average Monthly Household Online Expenditure by Type of Goods and Income Quintile (HES 2017/18) | `d_a5523e2bf61e9719aa328984493c8247` | CSV    | Expenditure patterns           |
| Resident Households By Type Of Dwelling, Annual                                                 | `d_edf8bb4773c25dd16b8b6875fd0b52da` | CSV    | **Dwelling type distribution** |

### Education

| Dataset                                                              | Resource ID                          | Format | Notes                       |
| -------------------------------------------------------------------- | ------------------------------------ | ------ | --------------------------- |
| Education Profile Of Singapore Residents Aged 25+ By HQA (%), Annual | `d_7317a32321dbfad2cbb5b60ca74c9f08` | CSV    | Education attainment trends |

---

## 8. Healthcare Facilities

| Dataset                                                    | Resource ID                           | Format  | Notes                               |
| ---------------------------------------------------------- | ------------------------------------- | ------- | ----------------------------------- |
| **Health Facilities (Primary Care, Dental, Pharmacies)**   | `d_e4663ad3f088a46dabd3972dc166402d`  | CSV     | **Clinic locations with breakdown** |
| **Health Facilities (Dental Clinics and Pharmacies)**      | `d_d4386b3130303e5f7ccbbfc785602a606` | CSV     | Dental + pharmacy counts            |
| **CHAS Clinics (GEOJSON)**                                 | `d_548c33ea2d99e29ec63a7cc9edcccedc`  | GEOJSON | **Subsidised clinic locations**     |
| **Public Health Preparedness Clinic (PHPC)**               | `d_d7865f18a9f49f7120f1fb6b3581bcd4`  | CSV     | GP clinic locations                 |
| Vaccination Polyclinics (GEOJSON)                          | `d_b22489c7dc4065b6e7e45f177fdb33be`  | GEOJSON | Polyclinic locations                |
| Health Facilities, Annual                                  | `d_e7fa2cba35ccc1173d941986e07b09df`  | CSV     | Annual facility counts              |
| Hospital Beds By Facility Type And Planning Region, Annual | `d_0ed27481bde3ad8abac12be380a441bb`  | CSV     | Healthcare capacity by region       |

---

## 9. Sports & Community Facilities

| Dataset                                        | Resource ID                          | Format  | Notes                      |
| ---------------------------------------------- | ------------------------------------ | ------- | -------------------------- |
| **SportSG Sport Facilities (GEOJSON)**         | `d_9b87bab59d036a60fad2a91530e10773` | GEOJSON | **All SportSG facilities** |
| SportSG DUS Sport Facilities (GEOJSON)         | `d_7ff555dfb7104533494b23a60188a044` | GEOJSON | Dual-use scheme            |
| Sport Facilities (CSV)                         | `d_2cfb0867cdeb2b7303068995699dc33b` | CSV     | SportDexSG listing         |
| SportsFields@SG (GEOJSON)                      | `d_f71b449b4b43a69b5ecfe411b440d249` | GEOJSON | Sports fields              |
| Parks@SG (GEOJSON)                             | `d_99b71f5d34cf57a3a592fbfdef1f42b6` | GEOJSON | Park locations             |
| **Community Clubs (GEOJSON)**                  | `d_f706de1427279e61fe41e89e24d440fa` | GEOJSON | **CC locations**           |
| Community Club / PAssion WaVe Outlet (GEOJSON) | `d_9de02d3fb33d96da1855f4fbef549a0f` | GEOJSON | CC + water sports          |
| **NParks Parks and Nature Reserves (GEOJSON)** | `d_77d7ec97be83d44f61b85454f844382f` | GEOJSON | **All parks/reserves**     |
| **Parks (GEOJSON)**                            | `d_0542d48f0991541706b58059381a6eca` | GEOJSON | Park point locations       |
| Park Facilities (GEOJSON)                      | `d_14d807e20158338fd578c2913953516e` | GEOJSON | Park facility points       |
| Park Connector Loop (GEOJSON)                  | `d_a69ef89737379f231d2ae93fd1c5707f` | GEOJSON | Park connector network     |
| NParks Tracks (GEOJSON)                        | `d_306cc1018cb733346681883ee6d73054` | GEOJSON | Hiking/walking tracks      |
| Community in Bloom (GEOJSON)                   | `d_f91a8b057cfb2bebf2e531ad8061e1c1` | GEOJSON | Community gardens          |
| NParks BBQ Pits (GEOJSON)                      | `d_5e5442d0766b00d2d09fd6f7768362a6` | GEOJSON | BBQ pit locations          |
| NParks Car Park Lots (GEOJSON)                 | `d_d5594e4c43e838380155f05f53f58567` | GEOJSON | Nature park parking        |

### Hawker Centres & Markets

| Dataset                                   | Resource ID                          | Format  | Notes                       |
| ----------------------------------------- | ------------------------------------ | ------- | --------------------------- |
| **Hawker Centres (GEOJSON)**              | `d_4a086da0a5553be1d89383cd90d07ecd` | GEOJSON | **Hawker centre locations** |
| List of Government Markets/Hawker Centres | `d_68a42f09f350881996d83f9cd73ab02f` | CSV     | Address + stall counts      |
| Licensed Supermarkets, Annual             | `d_34ba4c6d34d95f6bc06244917f62a0d8` | CSV     | NEA supermarket count       |
| List of Supermarket Licences              | `d_11edd0117280c5776651d7891114c88c` | CSV     | Supermarket locations       |

### Libraries

| Dataset       | Resource ID                          | Format | Notes                      |
| ------------- | ------------------------------------ | ------ | -------------------------- |
| Library (NLB) | `d_7e11775ef59f13278e1848cde57ce53a` | API    | REST API — library details |

### Childcare & Education

| Dataset                                                      | Resource ID                          | Format  | Notes                              |
| ------------------------------------------------------------ | ------------------------------------ | ------- | ---------------------------------- |
| **Pre-Schools Location (GEOJSON)**                           | `d_61eefab99958fd70e6aab17320a71f1c` | GEOJSON | **ECDA preschool locations**       |
| **General information of schools**                           | `d_688b934f82c1059ed0a6993d2a829089` | CSV     | **In pipeline** — school directory |
| Number Of Schools By Level, Type And Planning Region, Annual | `d_bdf12c8b14453f3ce847fac94cce4a3c` | CSV     | School counts by region            |

---

## 10. Government Land Sales & Vacant Land

| Dataset                                                | Resource ID                          | Format  | Notes                         |
| ------------------------------------------------------ | ------------------------------------ | ------- | ----------------------------- |
| **Industrial Government Land Sales — Sites (GEOJSON)** | `d_a751490a138b40eb13c48b0eb90e5c64` | GEOJSON | **JTC IGLS sites**            |
| **SLA Vacant State land and properties (GEOJSON)**     | `d_408e0ce796d119ea87b93b2d3402e134` | GEOJSON | **SLA vacant land inventory** |
| Community Use Sites (GEOJSON)                          | `d_1f35a697b1a83fc771fa528cf76bcea4` | GEOJSON | HDB/SLA community sites       |
| JTC Business Park Land (GEOJSON)                       | `d_7555d52fb87e75da7397bd65d4f107dd` | GEOJSON | Business park zones           |

---

## 11. Macro Economic Indicators

### Already In Use

| Dataset                                      | Resource ID                          | Status          |
| -------------------------------------------- | ------------------------------------ | --------------- |
| Consumer Price Index (CPI), Monthly          | `d_bdaff844e3ef89d39fceb962ff8f0791` | **In pipeline** |
| GDP In Chained (2015) Dollars                | `d_a5ff719648a0e6d4b4c623ee383ab686` | **In pipeline** |
| Unemployment Rate (End Of Period), Quarterly | `d_b0da22a41f952764376a2b7b5b0f2533` | **In pipeline** |

### Additional

| Dataset                                                  | Resource ID                          | Format | Notes                       |
| -------------------------------------------------------- | ------------------------------------ | ------ | --------------------------- |
| Overall Unemployment Rate, Quarterly (MOM)               | `d_ca32584c91ee07d091a4ce75fa868414` | CSV    | Alternative source          |
| Citizen Unemployment Rate, Quarterly                     | `d_1353f9be1a020ba1469852c49ee62db3` | CSV    | Citizen-specific            |
| Consumer Price Indices (CPI) — Healthcare                | `d_b7c2e74824c179995d15d73eac845ba1` | CSV    | MOH healthcare CPI          |
| Current Banks Interest Rates, Monthly                    | `d_5fe5a4bb4a1ecc4d8a56a095832e2b24` | CSV    | **Mortgage rate indicator** |
| Per Capita GDP In Chained (2015) Dollars, Annual         | `d_c43f61819c32009f2e86c29b0550e7fc` | CSV    | Per capita GDP              |
| Government Overall Fiscal Position (% Of GDP), Annual    | `d_9c0e02a3653b6b73cd3b7b6ec4263f71` | CSV    | Fiscal health               |
| Duty Rates for Lease/Mortgage/Share Transfer Duty        | `d_3365239a616d222d8060901fe6a8600b` | CSV    | IRAS stamp duty rates       |
| Changes In Average Monthly Nominal Earnings Per Employee | `d_64f98475cef1e94300362cb400a50012` | CSV    | Wage growth                 |

---

## 12. Other Useful Datasets

### Recycling & Waste

| Dataset                     | Resource ID                          | Format  | Notes                       |
| --------------------------- | ------------------------------------ | ------- | --------------------------- |
| Recycling Bins (GEOJSON)    | `d_4dde14826642f49eefff48b7832b90db` | GEOJSON | NEA recycling bin locations |
| E-waste Recycling (GEOJSON) | `d_db40d004afeb5a7f0f555fdcc34934cc` | GEOJSON | E-waste points              |

### Energy

| Dataset                                               | Resource ID                          | Format | Notes             |
| ----------------------------------------------------- | ------------------------------------ | ------ | ----------------- |
| Installed Capacity of Grid-Connected Solar PV Systems | `d_51adcf3cc50e30e25ad68c951743db69` | CSV    | Solar adoption    |
| Energy Consumption Per Dollar GDP                     | `d_0a6e94f474ada55c3e81d088463cf321` | CSV    | Energy efficiency |

### Internet / Broadband

| Dataset                                                   | Resource ID                          | Format | Notes               |
| --------------------------------------------------------- | ------------------------------------ | ------ | ------------------- |
| Residential Wired Broadband Subscriptions, Monthly        | `d_96289a87ccf826c81934c59cf69c512c` | CSV    | Connectivity metric |
| Fixed Broadband Plans and Prices                          | `d_7a7f9510c00914869094fb466a2c9e04` | CSV    | IMDA broadband      |
| Fixed Internet Broadband Subscriptions Per 100 Population | `d_27e16134218eed743a010297e66439fc` | CSV    | Penetration rate    |

---

## Summary: Top Priority New Datasets to Integrate

### Tier 1 — Immediate Value (High Impact Features)

1. **HDB Property Information** (`d_17f5382f26140b1fdae0ba2ef6239d2f`) — Block-level data for every HDB estate
2. **Master Plan 2025 Land Use Layer** (`d_a8c3546b26712e35021f3a681d0353ae`) — Latest zoning for all parcels
3. **Planning Area / Subzone Boundaries** (`d_4765db0e87b9c86336792efe8a1f7a66` / `d_8594ae9ff96d0c708bc2af633048edfb`) — Spatial joins
4. **LTA Bus Stop** (`d_3f172c6feb3f4f92a2f47d93eed2908a`) — All bus stop locations
5. **LTA MRT Station Exit** (`d_b39d3a0871985372d7e1637193335da5`) — MRT station exits
6. **Green Mark Buildings** (`d_da116ef216e3fb501846e1c9faf7e683`) — Green building proximity
7. **PSI / PM2.5 APIs** — Real-time air quality for environment scoring
8. **Flood Prone Areas** (`d_c4aed98f1533eb3a66f65dbb1a30da46`) — Flood risk scoring
9. **Cycling Path Network** (`d_8f468b25193f64be8a16fa7d8f60f553`) — Active mobility infrastructure
10. **CHAS Clinics** (`d_548c33ea2d99e29ec63a7cc9edcccedc`) — Healthcare proximity

### Tier 2 — Feature Enrichment (Medium Impact)

11. Private Property Price Index (`d_97f8a2e995022d311c6c68cfda6d034c`)
12. Supply Pipeline data (multiple URA datasets)
13. Pre-Schools Location (`d_61eefab99958fd70e6aab17320a71f1c`)
14. SportSG Sport Facilities (`d_9b87bab59d036a60fad2a91530e10773`)
15. Community Clubs (`d_f706de1427279e61fe41e89e24d440fa`)
16. Industrial GLS Sites (`d_a751490a138b40eb13c48b0eb90e5c64`)
17. SLA Vacant State Land (`d_408e0ce796d119ea87b93b2d3402e134`)
18. Census 2020 income/commute data by planning area
19. Current Banks Interest Rates (`d_5fe5a4bb4a1ecc4d8a56a095832e2b24`)
20. NEA historical weather data (rainfall, temperature by area)

### Tier 3 — Advanced Analytics (Future Enhancement)

21. HDB demographic datasets (population by town, flat type, ethnicity)
22. Transport mode share by planning area (Census 2020)
23. HDB upgrading programmes (LUP, NRP)
24. Solar PV adoption by area
25. URA hexagonal grids for spatial aggregation
26. Master Plan historical layers (2003, 2008, 2014) for temporal analysis
