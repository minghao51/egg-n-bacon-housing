"""Tests for pipeline modules."""

from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import pytest
from pathlib import Path

from scripts.core.pipeline.L0_collect import (
    fetch_datagovsg_dataset,
    fetch_private_property_transactions,
    load_resale_flat_prices,
    _convert_lease_to_months
)
from scripts.core.pipeline.L1_process import (
    load_and_save_transaction_data,
    prepare_unique_addresses,
    process_geocoded_results,
    save_failed_addresses
)


@pytest.fixture
def sample_api_response():
    """Sample data.gov.sg API response."""
    return {
        "result": {
            "records": [
                {"quarter": "2024-Q1", "value": 100},
                {"quarter": "2024-Q2", "value": 200}
            ],
            "total": 2,
            "_links": {}
        }
    }


class TestL0Collect:
    """Test L0 collection functions."""

    @patch('src.pipeline.L0_collect.cached_call')
    @patch('src.pipeline.L0_collect.requests.get')
    def test_fetch_datagovsg_dataset(self, mock_get, mock_cached_call):
        """Test fetching data from data.gov.sg API."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "result": {
                "records": [{"a": 1}, {"b": 2}],
                "total": 2,
                "_links": {}
            }
        }
        mock_get.return_value = mock_response

        # Mock cache miss
        mock_cached_call.side_effect = lambda cache_id, func, **kwargs: func()

        # Fetch data
        result = fetch_datagovsg_dataset(
            "https://api.test.com/",
            "test_id",
            use_cache=False
        )

        assert len(result) == 2
        assert 'a' in result.columns or 'b' in result.columns

    @patch('src.pipeline.L0_collect.save_parquet')
    @patch('src.pipeline.L0_collect.fetch_datagovsg_dataset')
    def test_fetch_private_property_transactions(self, mock_fetch, mock_save):
        """Test fetching private property transactions."""
        # Mock API response
        mock_df = pd.DataFrame({'quarter': ['2024-Q1'], 'value': [100]})
        mock_fetch.return_value = mock_df

        # Fetch
        result = fetch_private_property_transactions()

        # Verify save was called
        assert mock_save.called
        assert result is not None

    def test_convert_lease_to_months(self):
        """Test lease conversion function."""
        # Test various formats
        assert _convert_lease_to_months("61 years 04 months") == 736
        assert _convert_lease_to_months("60 years") == 720
        assert _convert_lease_to_months("05 months") == 5
        assert _convert_lease_to_months(99) == 99  # Already numeric
        assert _convert_lease_to_months(None) is None
        assert _convert_lease_to_months("") == 0

    @patch('src.pipeline.L0_collect.pd.read_csv')
    @patch('src.pipeline.L0_collect.Config')
    def test_load_resale_flat_prices(self, mock_config, mock_read_csv):
        """Test loading resale flat prices."""
        # Mock path
        mock_path = Mock()
        mock_path.glob.return_value = [
            Mock(name='file1.csv'),
            Mock(name='file2.csv')
        ]
        mock_config.DATA_DIR = Mock()
        mock_config.DATA_DIR.__truediv__ = Mock(return_value=mock_path)

        # Mock CSV reading
        mock_read_csv.return_value = pd.DataFrame({
            'month': ['2024-01'],
            'town': ['BISHAN'],
            'remaining_lease': ['61 years 04 months']
        })

        # Load
        result = load_resale_flat_prices()

        # Verify
        assert not result.empty
        assert 'remaining_lease_months' in result.columns


class TestL1Process:
    """Test L1 processing functions."""

    @patch('src.pipeline.L1_process.save_parquet')
    @patch('src.pipeline.L1_process.load_ura_files')
    def test_load_and_save_transaction_data(self, mock_load, mock_save):
        """Test loading and saving transaction data."""
        # Mock transaction data
        ec_df = pd.DataFrame({'property': ['EC1']})
        condo_df = pd.DataFrame({'property': ['Condo1']})
        res_df = pd.DataFrame({'property': ['Res1']})
        hdb_df = pd.DataFrame({'property': ['HDB1']})

        mock_load.return_value = (ec_df, condo_df, res_df, hdb_df)

        # Load
        result_ec, result_condo, result_res, result_hdb = load_and_save_transaction_data()

        # Verify all saves were called
        assert mock_save.call_count == 4
        assert len(result_ec) == 1
        assert len(result_condo) == 1

    @patch('src.pipeline.L1_process.extract_unique_addresses')
    def test_prepare_unique_addresses(self, mock_extract):
        """Test preparing unique addresses."""
        # Mock extraction
        mock_df = pd.DataFrame({
            'NameAddress': ['Address 1', 'Address 2'],
            'property_type': ['private', 'hdb']
        })
        mock_extract.return_value = mock_df

        # Prepare
        result = prepare_unique_addresses(
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame()
        )

        assert not result.empty
        assert 'NameAddress' in result.columns

    @patch('src.pipeline.L1_process.save_parquet')
    def test_process_geocoded_results(self, mock_save):
        """Test processing geocoded results."""
        # Create geocoded data
        geocoded_df = pd.DataFrame({
            'search_result': [0, 1, 0],  # Mix of best match and not
            'NameAddress': ['Addr1', 'Addr2', 'Addr3'],
            'X': ['100', '200', '300']
        })

        # Create housing data with property types
        housing_df = pd.DataFrame({
            'NameAddress': ['Addr1', 'Addr2', 'Addr3'],
            'property_type': ['private', 'hdb', 'private']
        })

        # Process
        result = process_geocoded_results(
            geocoded_df,
            housing_df,
            save_full=True,
            save_filtered=True
        )

        # Verify filtering
        assert len(result) == 2  # Only search_result == 0
        assert 'property_type' in result.columns
        assert all(result['search_result'] == 0)

    @patch('src.pipeline.L1_process.save_parquet')
    def test_process_geocoded_results_empty(self, mock_save):
        """Test processing empty geocoded results."""
        result = process_geocoded_results(
            pd.DataFrame(),
            pd.DataFrame(),
            save_full=True,
            save_filtered=True
        )

        assert result.empty

    @patch('src.pipeline.L1_process.Config')
    @patch('builtins.open')
    def test_save_failed_addresses(self, mock_open, mock_config):
        """Test saving failed addresses."""
        # Mock path
        mock_log_dir = Mock()
        mock_config.DATA_DIR = Mock()
        mock_config.DATA_DIR.__truediv__ = Mock(return_value=mock_log_dir)
        mock_log_dir.mkdir = Mock()

        failed = ['Address 1', 'Address 2', 'Address 3']

        # Save (should not raise exception)
        save_failed_addresses(failed)

        # Verify
        mock_open.assert_called_once()


class TestPipelineIntegration:
    """Integration tests for pipeline functions."""

    @patch('src.pipeline.L0_collect.requests.get')
    def test_full_l0_collection_workflow(self, mock_get):
        """Test complete L0 collection workflow."""
        # Mock API responses for multiple datasets
        def mock_response_func(url, *args, **kwargs):
            mock_resp = Mock()
            if 'd_5785799d63a9da091f4e0b456291eeb8' in url:
                mock_resp.json.return_value = {
                    "result": {
                        "records": [{"quarter": "2024-Q1"}],
                        "total": 1,
                        "_links": {}
                    }
                }
            else:
                mock_resp.json.return_value = {
                    "result": {
                        "records": [],
                        "total": 0,
                        "_links": {}
                    }
                }
            return mock_resp

        mock_get.side_effect = mock_response_func

        # This would test the full L0 collection
        # In practice, you'd mock save_parquet to avoid file I/O

    @patch('src.pipeline.L1_process.geocode_addresses')
    @patch('src.pipeline.L1_process.load_and_save_transaction_data')
    @patch('src.pipeline.L1_process.prepare_unique_addresses')
    @patch('src.pipeline.L1_process.process_geocoded_results')
    def test_full_l1_pipeline_workflow(
        self, mock_process, mock_prepare, mock_load, mock_geocode
    ):
        """Test complete L1 processing workflow."""
        # Mock transaction data
        mock_load.return_value = (
            pd.DataFrame({'Project Name': ['EC1']}),
            pd.DataFrame({'Project Name': ['Condo1']}),
            pd.DataFrame({'block': ['123']})
        )

        # Mock addresses
        mock_prepare.return_value = pd.DataFrame({
            'NameAddress': ['Address 1', 'Address 2'],
            'property_type': ['private', 'hdb']
        })

        # Mock geocoding
        mock_geocode.return_value = (
            pd.DataFrame({
                'search_result': [0, 0],
                'NameAddress': ['Address 1', 'Address 2']
            }),
            []
        )

        # Mock processing
        mock_process.return_value = pd.DataFrame({
            'search_result': [0, 0],
            'NameAddress': ['Address 1', 'Address 2'],
            'property_type': ['private', 'hdb']
        })

        # Run pipeline
        from core.pipeline.L1_process import run_processing_pipeline

        with patch('src.pipeline.L1_process.save_parquet'):
            results = run_processing_pipeline(use_parallel_geocoding=True)

        # Verify results
        assert 'transaction_counts' in results
        assert 'total_addresses' in results
        assert 'geocoded_count' in results
        assert 'filtered_count' in results
