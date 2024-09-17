import logging


logger = logging.getLogger(__name__)


def test_get_api_data(api_client, ingester):
    data_points_per_page = api_client.api_data_points_per_page
    data, failed_requests = ingester.get_api_data(max_page=1)
    assert len(data) == data_points_per_page
    assert isinstance(failed_requests, list)
