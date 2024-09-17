import pytest
import logging
from src.breweries.ingester import APITools
from breweries.ingester import Ingester
from pyspark.sql import SparkSession


logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def api_client():
    return APITools()


@pytest.fixture(scope="session")
def ingester():
    return Ingester()


@pytest.fixture(scope="session")
def spark():
    return (
        SparkSession
        .builder
        .master("local[*]")
        .appName("PySpark Example")
        .getOrCreate()
    )
