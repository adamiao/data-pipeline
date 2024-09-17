import time
import logging
import json
from pathlib import Path
from typing import Any
from breweries.utils import create_utc_timestamp_subdirectory
from breweries.paths import PATH_DATA_BRONZE
from breweries.api import APITools


logger = logging.getLogger(__name__)


class Ingester(APITools):

    def __init__(self):
        super(Ingester, self).__init__()

    def get_api_data(self, max_page: int=None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Returns the entire data provided by the API as well as a dataset linked to the failed data requests.
        :param max_page: [int] max number of pages requested
        :return: [tuple[list[dict[str, Any]], list[dict[str, Any]]]] 
        """
        # Ensure the value for "max_page" is correct for the API usage
        if max_page is None or max_page > self.api_max_page:
            max_page = self.api_max_page
        elif max_page < 1:
            max_page = self.api_min_page

        data, failed_requests = [], []
        params = {"page": self.api_min_page, "per_page": self.api_data_points_per_page}
        while params["page"] <= max_page:
            r = self.request_page(page=params["page"])

            # If request is not deemed successful we store that information for later recovery if necessary
            if r is None or r.status_code != 200:
                failed_requests += params
                logger.error(f"Failed request with parameters: {params}")
                params["page"] += 1
                continue

            # Ensure the data is being decoded correctly
            try:
                data_point = json.loads(r.content)
                data += data_point
            except Exception as e:
                logger.error(f"JSON decoding error while ingesting request with parameter {params}: {e}")
            finally:
                params["page"] += 1

            # Ensures we respect the API by not hitting it at a high request rate
            time.sleep(1 / self.api_request_rate)
        return data, failed_requests


    def data_quality(self, parent_directory: Path) -> bool:
        """
        Checks the quality of the ingested dataset.
        :param parent_directory: [Path] parent directory being checked or data quality
        :return: [bool]
        """
        try:
            with open(parent_directory.joinpath("data.raw"), "r") as f:
                data = json.load(f)
            with open(parent_directory.joinpath("failed_requests.raw"), "r") as f:
                failed_requests = json.load(f)
        except OSError as e:
            logger.error(e)
            return False

        # Quality checks based on ingested dataset sizes
        size_ingested_data, size_failed_requests = len(data), len(failed_requests)
        if size_ingested_data != self.api_total_data_points or size_failed_requests > 0:
            logger.error(
                "there is a mismatch between the number of data points ingested and the "
                "number of data points the API is currently serving."
            )
            return False
        return True

    def retry_failed_requests(self, parent_directory: Path, max_retries: int=5) -> bool:
        """
        Method to run the latest failed requested cases
        :return: [bool]
        """
        try:
            with open(parent_directory.joinpath("failed_requests.raw"), "r") as f:
                failed_requests = json.load(f)
            if len(failed_requests) == 0:
                return True
        except OSError as e:
            logger.error(e)
            return False

        list_boolean_successes = [False for _ in failed_requests]
        recovered_data = []

        for i, failed_request in enumerate(failed_requests):
            failed_request_retries = max_retries
            while failed_request_retries > 0 or list_boolean_successes[i]:
                r = self.request_page(page=failed_request["page"], api_data_points_per_page=failed_request["per_page"])
                if r.status_code == 200:
                    recovered_data += json.loads(r.content)
                    break
                failed_request_retries -= 1
            if failed_request_retries > 0:
                list_boolean_successes[i] = True

        if all(list_boolean_successes):
            # Open original dataset that had no requests issue
            with open(parent_directory.joinpath("data.raw"), "r") as f:
                original_data = json.load(f)

            # Combine the recovered dataset with the original dataset and overwrite the original
            data = original_data + recovered_data
            with open(parent_directory.joinpath("data.raw"), "w") as f:
                json.dump(data, f)

            # Update the failed request dataset to be empty
            with open(parent_directory.joinpath("failed_requests.raw"), "w") as f:
                json.dump([], f)
            return True

        return False


    def run_ingestion(self) -> bool:
        """
        Runs the ingestion pipeline, persists the data, and finally checks for data quality.
        :return: [bool]
        """
        # Gets the current UTC timestamp as a reference for when the data is getting requested
        rounded_utc_timestamp = round(time.time())
        output_directory = create_utc_timestamp_subdirectory(
            parent_directory=PATH_DATA_BRONZE,
            rounded_utc_timestamp=rounded_utc_timestamp,
        )

        data, failed_requests = self.get_api_data()

        with open(output_directory.joinpath("data.raw"), "w") as f:
            json.dump(data, f)

        with open(output_directory.joinpath("failed_requests.raw"), "w") as f:
            json.dump(failed_requests, f)

        # Checks the persisted bronze dataset for quality assurance
        is_bronze_data_correct = self.data_quality(parent_directory=output_directory)

        if not is_bronze_data_correct:
            retry_was_successful = self.retry_failed_requests(parent_directory=output_directory, max_retries=5)
            if retry_was_successful:
                return True

        return is_bronze_data_correct
