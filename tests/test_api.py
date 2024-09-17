import json
import logging


logger = logging.getLogger(__name__)


def test_max_page(api_client):
    api_number_of_data_points = api_client.get_api_number_of_data_points()
    a, b = divmod(api_number_of_data_points, api_client.api_data_points_per_page)
    if b > 0:
        a += 1
    assert api_client.api_max_page == a


def test_get_page(api_client):
    r = api_client.request_page(page=1)
    assert r.status_code == 200

    data = json.loads(r.content)
    assert len(data) == api_client.api_data_points_per_page
