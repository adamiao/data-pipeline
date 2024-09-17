import logging
import requests
import json
from typing import Optional


logger = logging.getLogger(__name__)


class APITools:

    def __init__(self, data_points_per_page: int=200):
        self.api_url = "https://api.openbrewerydb.org/v1/breweries"
        self.api_metadata_url = "https://api.openbrewerydb.org/v1/breweries/meta"
        self.api_data_points_per_page = data_points_per_page
        self.api_total_data_points = self.get_api_number_of_data_points()
        self.api_min_page = 1
        self.api_max_page = self.get_api_max_page()
        self.api_request_rate = 4

    def get_api_number_of_data_points(self) -> int:
        """
        This method retrieves the current number of total data points the API is serving.
        :return: [Optional[int]]
        """
        n_points = 0
        r = requests.get(self.api_metadata_url)
        if r.status_code == 200:
            meta = json.loads(r.content)
            n_points = meta.get("total")
            n_points = int(n_points) if n_points is not None else 0
        return n_points

    def get_api_max_page(self) -> int:
        """
        Based on the API number of points per page, this method will return the maximum page number which will still
        return non-empty data.
        :return: [int]
        """
        a, b = divmod(self.api_total_data_points, self.api_data_points_per_page)
        if b == 0:
            return a
        return a + 1

    def request_page(self, page: int, api_data_points_per_page: int=None) -> Optional[requests.models.Response]:
        """
        Get the requested object based on a page number
        :param page: [int] page number being requested
        :param api_data_points_per_page: [int] number of points per page requested to the API
        :return: [Optional[requests.models.Response]]
        """
        # Ensures the number of data points per page is not an integer or "None"
        if api_data_points_per_page is None or not isinstance(api_data_points_per_page, int):
            api_data_points_per_page = self.api_data_points_per_page

        # Ensures the correct value for the page number (when page is 0, it returns the same as when page is equal to 1)
        if page < self.api_min_page:
            page = self.api_min_page
        elif page > self.api_max_page:
            page = self.api_max_page

        try:
            r = requests.get(self.api_url, params={"page": page, "per_page": api_data_points_per_page})
        except requests.exceptions.RequestException as e:
            logger.error(e)
            return None
        return r

    def request_metadata(self) -> Optional[requests.models.Response]:
        """
        Requests metadata information from the API. This is useful because it will inform us of the maximum amount of
        points the API is currently serving.
        :return: [Optional[requests.models.Response]]
        """
        try:
            r = requests.get(self.api_metadata_url)
        except requests.exceptions.RequestException as e:
            logger.error(e)
            return None
        return r
