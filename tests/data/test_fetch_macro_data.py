# tests/data/test_fetch_macro_data.py
import pandas as pd

from scripts.data.fetch_macro_data import fetch_cpi_data, fetch_sora_rates


def test_fetch_sora_rates_returns_dataframe():
    """Test SORA rate fetching returns DataFrame with correct columns."""
    df = fetch_sora_rates()

    assert isinstance(df, pd.DataFrame)
    assert 'date' in df.columns
    assert 'sora_rate' in df.columns
    assert len(df) > 0

def test_fetch_cpi_returns_dataframe():
    """Test CPI fetching returns DataFrame."""
    df = fetch_cpi_data()

    assert isinstance(df, pd.DataFrame)
    assert 'date' in df.columns
    assert 'cpi' in df.columns
    assert len(df) > 0

def test_macro_data_saved_to_parquet():
    """Test macro data is saved to correct location."""
    from scripts.core.config import Config

    output_path = Config.DATA_DIR / 'raw_data' / 'macro' / 'sora_rates.parquet'

    fetch_sora_rates(save_path=output_path)

    assert output_path.exists()
    df = pd.read_parquet(output_path)
    assert len(df) > 0
