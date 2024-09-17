import logging
import json
from breweries.utils import get_most_recent_directory
from breweries.constants import BREWERY_TYPES
from breweries.paths import (
    PATH_DATA_BRONZE,
    PATH_DATA_SILVER,
    PATH_DATA_GOLD,
)
from pyspark.sql import (
    functions as F,
    types as T,
    DataFrame,
    SparkSession,
)


logger = logging.getLogger(__name__)


class Enricher:

    def __init__(self):
        self.spark = Enricher.get_spark_session()

    @staticmethod
    def get_spark_session() -> SparkSession:
        """
        Creates a spark session.
        :return: [SparkSession]
        """
        return (SparkSession
                .builder
                .master("local[*]")
                .appName("Breweries Data Pipeline")
                .getOrCreate()
        )

    @staticmethod
    def trim_dataframe(df: DataFrame) -> DataFrame:
        """
        Transformation to make sure the datasets do not have leading or trailing white spaces.
        :param df: [DataFrame]
        :return: [DataFrame]
        """
        df = df.select(*(F.trim(F.col(c)).alias(c) for c in df.columns))
        return df

    @staticmethod
    def update_column_data_types(df: DataFrame) -> DataFrame:
        """
        Transformation to update the data type of columns that were deemed necessary.
        :param df: [DataFrame]
        :return: [DataFrame]
        """
        df = (df
              .withColumn("latitude", F.col("latitude").cast(T.DoubleType()))
              .withColumn("longitude", F.col("longitude").cast(T.DoubleType()))
        )
        return df

    @staticmethod
    def check_brewery_types(df: DataFrame) -> DataFrame:
        """
        This method will filter the dataset for only the allowable brewery types as reported by the API. Interesting to
        note that the API currently is reporting wrong data since they are allowing "taproom" and "beergarden" into the
        brewery types.
        :param df: [DataFrame]
        :return: [DataFrame]
        """
        # Create boolean column checking whether brewery type indeed belongs to the allowable types
        df = df.withColumn("is_brewery_type_correct", F.col("brewery_type").isin(BREWERY_TYPES))

        # Filter out the cases for which the brewery type is incorrect
        df = df.filter(F.col("is_brewery_type_correct"))
        return df


    @staticmethod
    def select_columns(df: DataFrame) -> DataFrame:
        """
        Transformation to select the columns and their order for the input dataframe.
        :param df: [DataFrame]
        :return: [DataFrame]
        """
        df = df.select(
            [
                "id",
                "name",
                "brewery_type",
                "street",
                "city",
                "state",
                "state_province",
                "country",
                "latitude",
                "longitude",
                "website_url",
                "phone",
                "postal_code",
                "address_1",
                "address_2",
                "address_3",
            ]
        )
        return df

    def run_silver_enricher(self) -> bool:
        """
        Runs the silver medallion data pipeline and persists the data.
        :return: [bool]
        """
        # Start by checking the latest persisted data in the bronze medallion storage
        most_recent_bronze_data_directory = get_most_recent_directory(PATH_DATA_BRONZE)
        if most_recent_bronze_data_directory is None:
            raise ValueError(
                "There are currently no raw datasets for the bronze medallion storage. The data ingestor must "
                "be run first."
            )

        # Gets the current UTC timestamp as a reference for when the data is getting requested
        utc_timestamp = most_recent_bronze_data_directory.name
        try:
            with open(most_recent_bronze_data_directory.joinpath("data.raw"), "r") as f:
                data = json.load(f)
                df = self.spark.createDataFrame(data)
        except Exception as e:
            logger.error(f"loading the bronze medallion dataset as a PySpark dataframe failed with error: {e}")
            return False

        # Moves the PySpark dataframe through a series of transformations that will enhance its quality to be later
        # used for meaningful business metrics
        try:
            df = (df
                  .transform(Enricher.trim_dataframe)
                  .transform(Enricher.update_column_data_types)
                  .transform(Enricher.check_brewery_types)
                  .transform(Enricher.select_columns)
            )
        except Exception as e:
            logger.error(f"silver medallion transformations failed with error: {e}")
            return False

        # Saves the silver quality dataset in a folder with the same UTC timestamp value that was obtained from the
        # bronze medallion storage. First the output directory is created and put in string format (as opposed to a
        # Path object).
        PATH_DATA_SILVER.joinpath(utc_timestamp).mkdir(parents=True, exist_ok=True)
        save_directory = PATH_DATA_SILVER.joinpath(f"{utc_timestamp}")
        save_directory = "/".join(save_directory.parts)[1:]

        # The dataframe is partitioned by country where the brewery is located
        (df
         .write
         .mode("overwrite")
         .format("parquet")
         .option("encoding", "UTF-8")
         .partitionBy("country")
         .save(save_directory)
         )
        return True


    def run_gold_enricher(self) -> bool:
        """
        Runs the gold medallion data pipeline and persists the data.
        :return: [bool]
        """
        # Start by checking the latest persisted data in the silver medallion storage
        most_recent_silver_data_directory = get_most_recent_directory(PATH_DATA_SILVER)
        if most_recent_silver_data_directory is None:
            raise ValueError(
                "There are currently no raw datasets for the silver medallion storage. The first part of the enricher "
                "pipeline must be run first."
            )

        # Gets the UTC timestamp associated with the silver medallion data directory to later be used to store the gold
        # medallion dataset. Then write the directory in string format to load the parquet file.
        utc_timestamp = most_recent_silver_data_directory.name
        most_recent_silver_data_directory = "/".join(most_recent_silver_data_directory.parts)[1:]
        try:
            df = self.spark.read.parquet(most_recent_silver_data_directory)
        except Exception as e:
            logger.error(f"loading the silver medallion PySpark dataframe failed with error: {e}")
            return False

        try:
            df = df.groupby("country", "brewery_type").agg(F.count("*").alias("brewery_count"))
            df = df.orderBy("country", "brewery_type")
        except Exception as e:
            logger.error(f"creation of the gold medallion dataset failed with error: {e}")
            return False

        # Saves the gold quality dataset in a folder with the same UTC timestamp value that was obtained from the
        # bronze and silver medallion storage. Just like was done for the silver medallion pipeline, the output
        # directory is created and put in string format (as opposed to a Path object).
        PATH_DATA_GOLD.joinpath(utc_timestamp).mkdir(parents=True, exist_ok=True)
        save_directory = PATH_DATA_GOLD.joinpath(f"{utc_timestamp}")
        save_directory = "/".join(save_directory.parts)[1:]

        # Due to the size of the dataset we are dealing with, it is ok to have it repartitioned to only one file.
        df = df.repartition(1)

        # The dataframe is partitioned by country where the brewery is located
        (df
         .write
         .mode("overwrite")
         .format("parquet")
         .option("encoding", "UTF-8")
         .save(save_directory)
         )

        return True
