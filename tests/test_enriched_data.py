import json
import logging
from pyspark.sql import functions as F
from breweries.utils import get_most_recent_directory
from breweries.paths import (
    PATH_DATA_BRONZE,
    PATH_DATA_SILVER,
    PATH_DATA_GOLD,
)


logger = logging.getLogger(__name__)


def test_bronze_dataset(spark, api_client):
    api_number_of_data_points = api_client.get_api_number_of_data_points()
    most_recent_directory = get_most_recent_directory(PATH_DATA_BRONZE)
    with open(most_recent_directory.joinpath("data.raw"), "r") as f:
        data = json.load(f)
        df = spark.createDataFrame(data)
    assert df.count() == api_number_of_data_points
    assert len(df.columns) == 16


def test_silver_dataset(spark):
    most_recent_directory = get_most_recent_directory(PATH_DATA_SILVER)
    most_recent_directory = "/".join(most_recent_directory.parts)[1:]
    df = spark.read.parquet(most_recent_directory)
    assert df.count() > 8000
    assert len(df.columns) == 16

    data_types = [dtype for name, dtype in df.dtypes if name in ["latitude", "longitude"]]
    assert len(data_types) == 2
    assert data_types[0] == data_types[1] == "double"


def test_gold_dataset(spark):
    most_recent_directory = get_most_recent_directory(PATH_DATA_GOLD)
    most_recent_directory = "/".join(most_recent_directory.parts)[1:]
    df = spark.read.parquet(most_recent_directory)
    assert df.count() > 30
    assert df.groupby().agg(F.sum("brewery_count")).collect()[0][0] > 8000
    assert len(df.columns) == 3
