# Singapore Housing Price Visualization Dashboard

**Status**: ✅ MVP Complete
**Last Updated**: 2026-01-22

---

## 🚀 Quick Start

### **Run the Dashboard**

```bash
uv run streamlit run streamlit_app.py
```

The app will open in your browser at **http://localhost:8501**

### **Stop the Dashboard**

Press `Ctrl+C` in the terminal

---

## 📋 Features

### **1. Price Map** (Primary Feature)

Interactive map visualization with two modes:

#### **Heatmap Mode** (Default)
- **Performance optimized** for large datasets (>10K points)
- Color-coded by price (Blue = Low, Red = High)
- Hover tooltips showing property address and price
- Smooth zoom and pan

#### **Scatter Plot Mode**
- Individual property markers
- Sized by floor area
- Colored by price per square foot ($PSF)
- Optional amenity overlays (MRT, hawker, schools, parks)

### **2. Interactive Filters**

Located in the sidebar:

**Property Type**
- HDB
- Condominium
- Executive Condominium
- Landed

**Location**
- Town (26 HDB towns)
- Postal District (01-83)
- Street address (via search)

**Price**
- Minimum and maximum price range
- Floor area range (sqft)

**Time Period**
- Transaction date range
- From 2015 to present

**Map Settings**
- Toggle between Heatmap and Scatter views
- Show/hide amenity overlays
- Select which amenities to display

### **3. Market Overview**

High-level market statistics:
- Total transactions
- Median price
- Property type distribution
- Date range coverage

### **4. Export Functionality**

- Download filtered data as CSV
- Export current view for offline analysis

---

## 🏗️ Architecture

### **Project Structure**

```
egg-n-bacon-housing/
├── streamlit_app.py              # Main app entry point
├── core/
│   ├── data_loader.py            # Data loading with caching
│   └── map_utils.py              # Map visualization helpers
├── apps/
│   ├── 1_market_overview.py      # Market statistics
│   ├── 2_price_map.py            # Interactive map (MAIN)
│   └── 3_trends_analytics.py     # Coming soon
├── data/
│   └── parquets/
│       ├── L1/                   # Raw transaction data
│       ├── L2/                   # Geocoded + amenities
│       └── L3/                   # Advanced metrics
└── docs/
    └── 20260122-visualization-*.md
```

### **Technology Stack**

- **Framework**: Streamlit 1.31+
- **Visualization**: Plotly 6.5+
- **Maps**: OpenStreetMap (via Plotly)
- **Data**: Pandas 2.0+
- **Performance**: Caching with 1-hour TTL

---

## 📊 Data Integration

### **Data Sources**

**HDB Data** (L1)
- 969,748 resale transactions
- From data.gov.sg API
- Fields: month, town, flat_type, floor_area_sqm, resale_price, remaining_lease

**Condo Data** (L1)
- 49,052 private property transactions
- From URA (Urban Redevelopment Authority)
- Fields: Project Name, Transacted Price, Area (SQFT), Unit Price ($PSF)

**Geocoded Data** (L2)
- 17,720 unique properties with coordinates
- Via OneMap Singapore geocoding API
- Fields: lat, lon, postal, address

**Amenity Data** (L2)
- 5,569 amenity locations
- Types: MRT, hawker, schools, parks, childcare, preschool, supermarket
- Distance features: nearest within 500m/1km/2km

---

## 🎨 Customization

### **Dark Theme**

The app uses a dark theme for better visual contrast:
- Background: `#1e1e1e`
- Text: `#e0e0e0`
- Map: Carto Dark Matter tiles

### **Color Scale**

Price heatmap uses a 5-color scale:
- Blue (low prices)
- Green
- Yellow
- Orange
- Red (high prices)

### **Map Settings**

To change the map style, edit `core/map_utils.py`:

```python
# Dark theme (default)
DARK_THEME = "carto-darkmatter"

# Light theme
LIGHT_THEME = "open-street-map"
```

---

## ⚡ Performance

### **Optimizations**

1. **Data Caching**
   - 1-hour TTL on all data loads
   - Reduces loading time on subsequent visits

2. **Heatmap Mode**
   - Uses `density_mapbox` for automatic aggregation
   - Handles 10K+ points smoothly

3. **Lazy Loading**
   - Data loaded only when needed
   - Progress indicators for long operations

4. **Filter Efficiency**
   - Filters applied before rendering
   - Reduces data passed to visualization

### **Performance Tips**

- Use **Heatmap mode** for large datasets (>5K points)
- Apply filters to reduce data size
- Narrow time range for faster queries
- Switch to Scatter mode only for detailed exploration

---

## 🔧 Configuration

### **Environment Variables**

Create a `.env` file in the project root:

```bash
# Currently using OpenStreetMap (free, no token required)
# If you want to switch to Mapbox in the future:
MAPBOX_TOKEN=your_mapbox_public_token_here
```

### **Data Paths**

Edit `core/data_loader.py` to change data locations:

```python
DATA_DIR = Path("data/parquets")
```

---

## 🐛 Troubleshooting

### **"No data available" Error**

**Cause**: Data files not found

**Solution**:
1. Check that `data/parquets/L1/` and `data/parquets/L2/` exist
2. Verify that parquet files are present
3. Run L2 pipeline if needed: `uv run python scripts/run_l2_pipeline.py`

### **Map Not Displaying**

**Cause**: Invalid coordinates or empty data after filtering

**Solution**:
1. Try relaxing filters (wider date range, all towns)
2. Check data has valid lat/lon coordinates
3. Look for warnings in the UI

### **Slow Performance**

**Cause**: Too many points in Scatter mode

**Solution**:
1. Switch to Heatmap mode
2. Apply more filters to reduce data size
3. Reduce time range (e.g., last 2 years instead of all)

### **Import Errors**

**Cause**: Missing dependencies

**Solution**:
```bash
uv sync
```

---

## 🚧 Roadmap

### **Phase 1: MVP** ✅ (Complete)
- [x] Basic data loading with caching
- [x] Interactive map with heatmap
- [x] Property filters (type, town, price, time)
- [x] Amenity overlays
- [x] Export functionality

### **Phase 2: Advanced Features** (Next)
- [ ] Customizable trend charts (monthly/quarterly/yearly)
- [ ] Comparative analysis (by town, property type)
- [ ] Rental yield visualization
- [ ] ROI score display
- [ ] Time-series animation

### **Phase 3: Polish & Optimize**
- [ ] User documentation and help tooltips
- [ ] Responsive design improvements
- [ ] Error handling and validation
- [ ] Performance profiling and optimization
- [ ] Unit tests for critical functions

---

## 📝 Development Notes

### **Adding New Features**

1. **New Page**: Create `apps/4_new_page.py` and add to `streamlit_app.py`
2. **New Filter**: Add to `apps/2_price_map.py` render_filters() function
3. **New Metric**: Add to `core/data_loader.py` aggregation functions
4. **New Visualization**: Add to `core/map_utils.py` or create new module

### **Code Style**

- Follow PEP 8 guidelines
- Use type hints for functions
- Add docstrings for all modules and functions
- Keep functions focused and modular

### **Testing**

Test data loading:
```bash
uv run python -c "from core.data_loader import load_combined_data; df = load_combined_data(); print(df.head())"
```

Test map utilities:
```bash
uv run python -c "from core.map_utils import create_base_map; fig = create_base_map(); print('Map created successfully')"
```

---

## 🤝 Contributing

### **Best Practices**

1. **Small Changes**: Keep commits atomic and focused
2. **Test First**: Test locally before committing
3. **Documentation**: Update docs for new features
4. **Performance**: Profile before optimizing

### **Pull Request Process**

1. Create feature branch from `main`
2. Implement changes with tests
3. Update documentation
4. Submit PR with description

---

## 📄 License

This project is part of the egg-n-bacon-housing repository.

---

## 📞 Support

For issues or questions:
1. Check this README
2. Review the implementation plan: `docs/20260122-visualization-implementation-plan.md`
3. Check inline code comments
4. Open an issue on GitHub

---

**Enjoy exploring Singapore housing prices! 🏠🗺️**
