import click
import logging
import breweries.ingester as ip
import breweries.enricher as ep
from breweries import __version__


logger = logging.getLogger(__name__)


@click.command()
@click.option("--version", "-v", is_flag=True, help="Return version number.")
@click.option("--run-ingestion", "-ri",
              help="Run the ingestion pipeline.",
              is_flag=True,
              type=str,
              )
@click.option("--run-enricher", "-re",
              help="Run the enricher pipeline.",
              is_flag=True,
              type=str,
              )
@click.option("--run-all",
              help="Run the end-to-end data pipeline.",
              is_flag=True,
              type=str,
              )
def main(version, run_ingestion, run_enricher, run_all):
    if version:
        click.echo(f"'breweries' version: {__version__}")

    if run_ingestion:
        run_ingestion_pipeline()

    if run_enricher:
        run_enricher_pipeline()

    if run_all:
        run_ingestion_pipeline()
        run_enricher_pipeline()


def run_ingestion_pipeline():
        logger.info("ingestion pipeline started")
        ingester = ip.Ingester()
        successful = ingester.run_ingestion()
        if not successful:
            logger.error("data ingestion was not successful")
        logger.info("ingestion pipeline ended")


def run_enricher_pipeline():
        logger.info("enricher pipeline started")
        enricher = ep.Enricher()
        logger.info("silver medallion data processing has started")
        is_silver_successful = enricher.run_silver_enricher()
        logger.info("silver medallion data processing has ended")
        logger.info("gold medallion data processing has started")
        is_gold_successful = enricher.run_gold_enricher()
        logger.info("gold medallion data processing has ended")
        if not is_silver_successful:
            logger.error("data enricher for the silver medallion pipeline was not successful")
        if not is_gold_successful:
            logger.error("data enricher for the gold medallion pipeline was not successful")
        logger.info("enricher pipeline ended")
