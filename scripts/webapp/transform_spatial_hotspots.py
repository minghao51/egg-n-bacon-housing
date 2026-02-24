#!/usr/bin/env python3
"""Transform spatial hotspots data from towns[] format to clusters[] format.

The SpatialHotspotExplorer component expects data grouped by cluster type,
but the current data has individual town entries. This script transforms
the data structure.
"""

import json
import gzip
from datetime import datetime
from pathlib import Path


def transform_spatial_hotspots():
    """Transform spatial hotspots data to expected cluster format."""
    input_path = Path('app/public/data/interactive_tools/spatial_hotspots.json.gz')
    output_path = Path('app/public/data/interactive_tools/spatial_hotspots.json.gz')

    # Load current data
    print(f"Loading data from {input_path}...")
    with gzip.open(input_path, 'rt') as f:
        data = json.load(f)

    # Group towns by cluster type
    clusters = {}
    for town in data['towns']:
        cluster_type = town['cluster']
        if cluster_type not in clusters:
            clusters[cluster_type] = {
                'towns': [],
                'appreciation_rates': [],
                'prices': [],
                'persistence_probs': []
            }
        clusters[cluster_type]['towns'].append(town['town'])
        clusters[cluster_type]['appreciation_rates'].append(town['appreciation_rate'])
        clusters[cluster_type]['prices'].append(town['median_price'])
        clusters[cluster_type]['persistence_probs'].append(town['persistence_probability'])

    # Build clusters array in consistent order
    risk_levels = {'HH': 'Low', 'LH': 'Low', 'HL': 'Medium', 'LL': 'High'}
    cluster_list = []

    for cluster_type in ['HH', 'LH', 'HL', 'LL']:
        if cluster_type in clusters:
            values = clusters[cluster_type]
            cluster_list.append({
                'cluster_type': cluster_type,
                'towns': sorted(values['towns']),
                'avg_appreciation_5y': round(
                    sum(values['appreciation_rates']) / len(values['appreciation_rates']), 2
                ),
                'avg_price_psf': round(
                    sum(values['prices']) / len(values['prices']), 0
                ),
                'persistence_probability': round(max(values['persistence_probs']), 2),
                'risk_level': risk_levels[cluster_type]
            })

            print(f"  {cluster_type}: {len(values['towns'])} towns, "
                  f"avg appreciation: {cluster_list[-1]['avg_appreciation_5y']}%")

    # Create output with metadata
    output_data = {
        'clusters': cluster_list,
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        'methodology': (
            "Spatial autocorrelation using Moran's I statistic. "
            "HH = Hotspots (high appreciation, low risk), "
            "LL = Coldspots (low appreciation, high risk), "
            "LH = Emerging hotspots (growth potential), "
            "HL = Cooling areas (declining appreciation)."
        )
    }

    # Write compressed output
    print(f"\nWriting {len(cluster_list)} clusters to {output_path}...")
    with gzip.open(output_path, 'wt') as f:
        json.dump(output_data, f)

    print(f"✅ Successfully transformed spatial hotspots data")
    print(f"   - Clusters: {len(cluster_list)}")
    print(f"   - Total towns: {sum(len(c['towns']) for c in cluster_list)}")
    print(f"   - Analysis date: {output_data['analysis_date']}")


if __name__ == '__main__':
    transform_spatial_hotspots()
