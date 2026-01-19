# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.0
#   kernelspec:
#     display_name: py311cv
#     language: python
#     name: python3
# ---

# %%
import h3

# Sample latitude and longitude
lat = 37.7749
lon = -122.4194

# Encode into a hexagon at resolution 9
hex_address = h3.geo_to_h3(lat, lon, 9)

print(hex_address)


# %%
# Decode the hexagon back to latitude and longitude
lat_lon = h3.h3_to_geo(hex_address)
lat_lon

# %% [markdown]
# ## get a hexagon and its surrounding grids

# %%
# Define the center latitude and longitude
lat = 37.7749
lon = -122.4194

# Define the resolution
resolution = 3

# Get the hexagon address for the center point
center_hex = h3.geo_to_h3(lat, lon, resolution)

# Get the surrounding hexagons within 2 rings
surrounding_hexes = h3.k_ring(center_hex, 2)

print("Center Hex:", center_hex)
print("Surrounding Hexes:", surrounding_hexes)

# %%
