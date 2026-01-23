# Singapore Housing Price Visualization - Implementation Plan

**Date**: 2026-01-22
**Status**: Planning Phase
**Target**: Interactive Streamlit Dashboard with Mapbox

---

## 🎯 Design Decisions (Confirmed)

1. **Map Provider**: OpenStreetMap (free, no token required) via Plotly
2. **Theme**: Dark theme for better visual contrast
3. **Default View**: Heatmap for performance + toggleable points
4. **Amenity Display**: Point overlays for individual postcodes/amenities
5. **Time Granularity**: Customizable (Monthly/Quarterly/Yearly)
6. **Platform**: Desktop-first (responsive but optimized for desktop)
7. **Data Source**: Static parquet files (no real-time APIs)
8. **Initial Load**: Load all data by default

---

## 🏗️ Technical Architecture

### **App Structure**

```
streamlit_app.py                    # Main entry point
├── apps/
│   ├── 1_market_overview.py       # Dashboard summary
│   ├── 2_price_map.py             # Mapbox visualization (PRIMARY)
│   ├── 3_trends_analytics.py      # Time-series trends
│   └── 4_property_explorer.py     # Detailed property search
└── src/
    ├── data_loader.py             # Data loading & caching utilities
    ├── map_utils.py               # Mapbox rendering functions
    ├── filters.py                 # Filter logic and state management
    └── chart_utils.py             # Plotly/Altair chart helpers
```

### **Technology Stack**

```python
Core Framework:
- streamlit >= 1.31.0              # Main app framework
- pandas >= 2.0.0                  # Data manipulation
- numpy >= 1.24.0                  # Numerical operations

Visualization:
- plotly >= 5.18.0                 # Interactive charts
- mapbox >= 1.0.0                  # Map integration
- streamlit-elements              # Advanced UI components

Performance:
- cachetools >= 5.3.0              # Caching utilities
- polars >= 0.20.0 (optional)      # Faster data processing

Utilities:
- python-dotenv                    # Environment variables
- pydantic >= 2.0.0                # Data validation
```

---

## 📊 Data Pipeline

### **Data Sources & Integration**

```python
# L1: Raw Transactions
L1/hdb_resale.parquet              # 969,748 HDB transactions
L1/condo_ura.parquet               # 49,052 Condo transactions

# L2: Geocoded + Amenity Features
L2/housing_unique_searched.parquet # 17,720 unique properties (with lat/lon)
L2/amenity_features.parquet         # Distances to MRT, hawker, schools, parks

# L3: Advanced Metrics (Optional - Phase 2)
L3/price_growth.parquet            # Price growth rates by town/area
L3/rental_yield.parquet            # Rental yield calculations
```

### **Data Loading Strategy**

```python
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_hdb_data() -> pd.DataFrame:
    """Load HDB transaction data with optimized dtypes"""
    return pd.read_parquet("data/parquets/L1/hdb_resale.parquet")

@st.cache_data(ttl=3600)
def load_condo_data() -> pd.DataFrame:
    """Load Condo transaction data"""
    return pd.read_parquet("data/parquets/L1/condo_ura.parquet")

@st.cache_data(ttl=3600)
def load_geocoded_properties() -> pd.DataFrame:
    """Load geocoded unique properties"""
    return pd.read_parquet("data/parquets/L2/housing_unique_searched.parquet")

@st.cache_data(ttl=3600)
def load_amenity_features() -> pd.DataFrame:
    """Load amenity distance features"""
    return pd.read_parquet("data/parquets/L2/amenity_features.parquet")
```

---

## 🗺️ Map Visualization Strategy

### **Dual-Mode Map Implementation**

#### **Mode 1: Heatmap (Default)**

```python
import plotly.express as px
import plotly.graph_objects as go

def create_price_heatmap(
    df: pd.DataFrame,
    color_column: str = "resale_price",
    radius: int = 10
) -> go.Figure:
    """
    Create density heatmap for price visualization

    Uses Plotly's density_mapbox for performance with large datasets
    - Aggregates points into hexagonal bins
    - Color-coded by median price
    - Handles 10K+ points efficiently
    """

    fig = go.Figure(go.Densitymapbox(
        lat=df['lat'],
        lon=df['lon'],
        z=df[color_column],
        radius=radius,
        colorscale='Viridis',
        zmin=df[color_column].quantile(0.1),
        zmax=df[color_column].quantile(0.9),
        text=df['address'],  # Hover tooltip
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Price: $%{z:,.0f}<br>"
            "<extra></extra>"
        )
    ))

    fig.update_layout(
        mapbox=dict(
            style="carto-darkmatter",  # Dark theme for better contrast
            accesstoken=st.session_state['GOOGLE_API_KEY'],
            center=dict(lat=1.3521, lon=103.8198),  # Singapore center
            zoom=11
        ),
        height=700,
        margin=dict(l=0, r=0, t=0, b=0)
    )

    return fig
```

#### **Mode 2: Scatter Plot with Amenity Overlays**

```python
def create_scatter_map_with_amenities(
    properties_df: pd.DataFrame,
    amenities_df: pd.DataFrame,
    selected_amenities: List[str] = None
) -> go.Figure:
    """
    Create scatter plot with amenity overlays

    - Properties as circles (sized by price/floor area)
    - Amenities as icons (MRT, hawker, schools, parks)
    - Click to show property details
    - Filterable by amenity type
    """

    fig = go.Figure()

    # Add properties
    fig.add_trace(go.Scattermapbox(
        lat=properties_df['lat'],
        lon=properties_df['lon'],
        mode='markers',
        marker=dict(
            size=properties_df['floor_area_sqft'] / 100,  # Size by area
            color=properties_df['price_psf'],
            colorscale='RdYlGn',
            opacity=0.7,
            colorbar=dict(title="Price ($PSF)")
        ),
        text=properties_df['address'],
        hovertemplate=(
            "<b>%{text}</b><br>"
            "Price: $%{marker.color:.0f} PSF<br>"
            "Area: %{customdata[0]} sqft<br>"
            "<extra></extra>"
        ),
        customdata=properties_df[['floor_area_sqft', 'resale_price']],
        name='Properties'
    ))

    # Add amenity overlays
    if selected_amenities:
        amenity_icons = {
            'mrt': 'rail',
            'hawker': 'restaurant',
            'school': 'school',
            'park': 'park'
        }

        for amenity_type in selected_amenities:
            amenity_subset = amenities_df[
                amenities_df['amenity_type'] == amenity_type
            ]

            fig.add_trace(go.Scattermapbox(
                lat=amenity_subset['lat'],
                lon=amenity_subset['lon'],
                mode='markers',
                marker=dict(
                    size=10,
                    symbol=amenity_icons.get(amenity_type, 'circle'),
                    color='orange'
                ),
                text=amenity_subset['name'],
                hovertemplate="<b>%{text}</b><extra></extra>",
                name=amenity_type.capitalize()
            ))

    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            accesstoken=st.session_state['GOOGLE_API_KEY'],
            center=dict(lat=1.3521, lon=103.8198),
            zoom=12
        ),
        height=700,
        hovermode='closest'
    )

    return fig
```

### **View Switching Logic**

```python
def render_map_tab():
    """Render map tab with toggle between heatmap and scatter"""

    col1, col2 = st.columns([3, 1])

    with col1:
        view_mode = st.radio(
            "View Mode",
            ["Heatmap (Fast)", "Scatter (Detailed)"],
            horizontal=True
        )

    with col2:
        show_amenities = st.multiselect(
            "Show Amenities",
            ["MRT", "Hawker", "Schools", "Parks"],
            default=["MRT"]
        )

    # Load filtered data
    filtered_df = load_filtered_data()

    if view_mode == "Heatmap (Fast)":
        fig = create_price_heatmap(filtered_df)
    else:
        # Show amenity overlays only in scatter mode
        amenities_df = load_amenity_features()
        fig = create_scatter_map_with_amenities(
            filtered_df,
            amenities_df,
            selected_amenities=show_amenities
        )

    st.plotly_chart(fig, use_container_width=True)

    # Performance warning for large datasets
    if view_mode == "Scatter (Detailed)" and len(filtered_df) > 5000:
        st.warning(
            f"⚠️ Showing {len(filtered_df):,} points. "
            "For better performance, apply filters or switch to Heatmap mode."
        )
```

---

## 🎛️ Sidebar Filters Design

### **Filter Hierarchy**

```python
def render_filters():
    """Render all filter controls in sidebar"""

    st.sidebar.header("🔍 Filters")

    # 1. Property Type (Top-level filter)
    property_types = st.sidebar.multiselect(
        "Property Type",
        ["HDB", "Condominium", "Executive Condominium", "Landed"],
        default=["HDB", "Condominium"]
    )

    # 2. Location Filters
    st.sidebar.subheader("📍 Location")

    towns = st.sidebar.multiselect(
        "Town",
        sorted(TOWNS),  # 26 HDB towns
        default=None
    )

    planning_areas = st.sidebar.multiselect(
        "Planning Area",
        sorted(PLANNING_AREAS),  # URA planning areas
        default=None
    )

    postal_districts = st.sidebar.slider(
        "Postal District",
        1, 83,
        (1, 83),
        help="Singapore postal districts (01-83)"
    )

    # 3. Price Filters
    st.sidebar.subheader("💰 Price")

    price_range = st.sidebar.slider(
        "Price Range (SGD)",
        100000, 10000000,
        (100000, 3000000),
        step=50000,
        format="$%d"
    )

    floor_area = st.sidebar.slider(
        "Floor Area (sqft)",
        300, 10000,
        (500, 2000),
        step=50
    )

    # 4. Time Period
    st.sidebar.subheader("📅 Time Period")

    date_range = st.sidebar.slider(
        "Transaction Period",
        datetime(2015, 1, 1),
        datetime(2025, 12, 31),
        (datetime(2020, 1, 1), datetime(2024, 12, 31))
    )

    # 5. Amenity Filters
    st.sidebar.subheader("🏪 Amenity Proximity")

    amenity_filters = {
        'mrt': st.sidebar.selectbox(
            "MRT Within",
            ["Any", "500m", "1km", "2km"],
            index=1
        ),
        'hawker': st.sidebar.selectbox(
            "Hawker Within",
            ["Any", "500m", "1km", "2km"],
            index=2
        ),
        'school': st.sidebar.selectbox(
            "Schools Within",
            ["Any", "1km", "2km"],
            index=1
        ),
        'park': st.sidebar.selectbox(
            "Parks Within",
            ["Any", "500m", "1km"],
            index=1
        )
    }

    # 6. Advanced Filters (Collapsible)
    with st.sidebar.expander("⚙️ Advanced"):
        lease_remaining = st.slider(
            "Remaining Lease (HDB)",
            30, 99,
            (60, 99),
            help="Minimum remaining lease years"
        )

        floor_range = st.selectbox(
            "Floor Level",
            ["Any", "Low (1-5)", "Mid (6-10)", "High (11+)"]
        )

    return {
        'property_types': property_types,
        'towns': towns,
        'planning_areas': planning_areas,
        'postal_districts': postal_districts,
        'price_range': price_range,
        'floor_area': floor_area,
        'date_range': date_range,
        'amenity_filters': amenity_filters,
        'lease_remaining': lease_remaining,
        'floor_range': floor_range
    }
```

---

## 📈 Customizable Trend Charts

### **Time Granularity Selector**

```python
def render_trends_tab(df: pd.DataFrame):
    """Render time-series trend charts with customizable granularity"""

    col1, col2, col3 = st.columns([2, 2, 3])

    with col1:
        granularity = st.selectbox(
            "Time Granularity",
            ["Monthly", "Quarterly", "Yearly"],
            index=0
        )

    with col2:
        metric = st.selectbox(
            "Metric",
            ["Median Price", "Transaction Volume", "Price Growth (%)",
             "Rental Yield (%)", "Price ($ PSF)"],
            index=0
        )

    with col3:
        comparison = st.selectbox(
            "Compare By",
            ["None", "Town", "Property Type", "Flat Type"],
            index=0
        )

    # Aggregate data based on granularity
    df_agg = aggregate_by_timeperiod(df, granularity)

    # Create interactive plot
    fig = create_trend_chart(df_agg, metric, comparison)

    st.plotly_chart(fig, use_container_width=True)

    # Show statistics table
    if st.checkbox("Show Data Table"):
        st.dataframe(
            df_agg.pivot_table(
                index='period',
                columns=comparison if comparison != "None" else None,
                values=metric.lower().replace(" ", "_")
            ).reset_index(),
            use_container_width=True
        )
```

### **Trend Aggregation Logic**

```python
def aggregate_by_timeperiod(
    df: pd.DataFrame,
    granularity: str
) -> pd.DataFrame:
    """
    Aggregate transaction data by time period

    Args:
        df: Transaction data with 'month' column
        granularity: 'Monthly', 'Quarterly', or 'Yearly'

    Returns:
        Aggregated DataFrame with time period as index
    """

    df = df.copy()

    # Convert month to datetime if needed
    df['date'] = pd.to_datetime(df['month'])

    # Create time period grouping
    if granularity == "Monthly":
        df['period'] = df['date'].dt.to_period('M')
    elif granularity == "Quarterly":
        df['period'] = df['date'].dt.to_period('Q')
    else:  # Yearly
        df['period'] = df['date'].dt.to_period('Y')

    # Aggregate metrics
    agg_df = df.groupby('period').agg({
        'resale_price': ['median', 'count', 'std'],
        'floor_area_sqm': 'median',
        'price_psf': 'median'
    }).reset_index()

    agg_df.columns = [
        'period', 'median_price', 'transaction_count',
        'price_std', 'median_floor_area', 'median_psf'
    ]

    # Calculate growth rate
    agg_df['price_growth_pct'] = agg_df['median_price'].pct_change() * 100

    return agg_df
```

---

## 🚀 Implementation Phases

### **Phase 1: MVP (Week 1)**

**Goal**: Basic functional dashboard

- [x] Set up Streamlit app structure
- [ ] Implement data loading with caching
- [ ] Create sidebar filters (property type, town, price)
- [ ] Build basic Mapbox heatmap
- [ ] Add simple trend line chart
- [ ] Property details table view

**Success Criteria**:
- Load and display HDB + Condo data
- Filter by property type and town
- Show price heatmap
- Display median price trend over time

### **Phase 2: Advanced Features (Week 2)**

**Goal**: Enhanced interactivity

- [ ] Amenity-based filtering (MRT, schools, etc.)
- [ ] Scatter plot with amenity overlays
- [ ] Toggle between heatmap/point views
- [ ] Comparative analysis (box plots, scatter)
- [ ] Customizable time granularity
- [ ] Export filtered data to CSV

**Success Criteria**:
- Show amenities on map
- Switch between heatmap/scatter
- Compare prices by town/property type
- Export functionality

### **Phase 3: Polish & Optimize (Week 3)**

**Goal**: Production-ready

- [ ] Performance optimization (lazy loading, sampling)
- [ ] Responsive design improvements
- [ ] Error handling and validation
- [ ] User documentation (help tooltips)
- [ ] Loading spinners and progress indicators
- [ ] Unit tests for critical functions

**Success Criteria**:
- Map loads in <3 seconds
- Handles 10K+ points smoothly
- Clean UI/UX
- Stable and bug-free

---

## 💻 Key Implementation Details

### **1. Mapbox Token Configuration**

```python
# In streamlit_app.py
import os
from dotenv import load_dotenv

load_dotenv()

# Set Mapbox token
if 'mapbox_token' not in st.session_state:
    st.session_state.mapbox_token = os.getenv("MAPBOX_TOKEN")

# Alternative: Use token input in sidebar
if not st.session_state.mapbox_token:
    st.session_state.mapbox_token = st.sidebar.text_input(
        "Mapbox Token",
        type="password",
        help="Enter your Mapbox public token"
    )
```

### **2. Performance Optimization**

```python
# Data sampling for quick preview
def load_data_sample(sample_size: int = 1000):
    """Load random sample for initial display"""
    df = load_filtered_data()
    if len(df) > sample_size:
        return df.sample(n=sample_size, random_state=42)
    return df

# Progressive loading
@st.cache_data
def load_data_in_chunks(chunk_size: int = 5000):
    """Load data in chunks for large datasets"""
    chunks = []
    for chunk in pd.read_parquet("large_file.parquet", chunksize=chunk_size):
        chunks.append(chunk)
    return pd.concat(chunks)
```

### **3. State Management**

```python
# Initialize session state
if 'filters' not in st.session_state:
    st.session_state.filters = {}

if 'selected_property' not in st.session_state:
    st.session_state.selected_property = None

if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'heatmap'
```

---

## 📝 File Structure

```
egg-n-bacon-housing/
├── streamlit_app.py              # Main app entry
├── apps/
│   ├── __init__.py
│   ├── 1_market_overview.py      # Dashboard summary
│   ├── 2_price_map.py            # Map visualization (PRIMARY)
│   ├── 3_trends_analytics.py     # Trend analysis
│   └── 4_property_explorer.py    # Property details
├── src/
│   ├── __init__.py
│   ├── data_loader.py            # Data loading utilities
│   ├── map_utils.py              # Mapbox helpers
│   ├── filters.py                # Filter logic
│   └── chart_utils.py            # Chart helpers
├── data/
│   └── parquets/
│       ├── L1/
│       ├── L2/
│       └── L3/
├── .env                          # API keys
├── pyproject.toml                # Dependencies
└── README.md
```

---

## 🎯 Next Steps

1. **Install Dependencies**
   ```bash
   uv add streamlit plotly mapbox streamlit-elements cachetools
   ```

2. **Create App Skeleton**
   - Set up multi-page Streamlit structure
   - Create `src/` utilities modules
   - Configure .env for Mapbox token

3. **Build MVP**
   - Implement data loading
   - Create basic filters
   - Build Mapbox heatmap
   - Add trend chart

4. **Test & Iterate**
   - Test with real data
   - Gather feedback
   - Optimize performance

---

## 🤔 Open Questions

1. **Mapbox Token**: Do you have a Mapbox public token, or should we use an alternative (e.g., OpenStreetMap)?

2. **Color Scheme**: Any preference for map colors (dark theme, light theme, custom)?

3. **Default Filters**: What should be the default view (all property types, specific date range, etc.)?

4. **Metrics Priority**: Which metrics are most important (price, rental yield, ROI score)?

5. **Mobile Support**: Should we optimize for tablets, or desktop-only is fine?

---

**Ready to proceed with implementation?**
