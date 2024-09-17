# Brewery Data Ingestion and Enrichment Tool
![Deploy badge](https://github.com/adamiao/data-pipeline/actions/workflows/main.yml/badge.svg)

# Table of Contents

1. [Overview](#overview)
2. [Data Ingestion](#data-ingestion)
3. [Data Enrichment](#data-enrichment)
4. [Error Handling and Logging](#error-handling-and-logging)
5. [Testing](#testing)
6. [Installation](#installation)
   1. [Virtual Environment](#installation-virtual-environment)
   2. [Docker](#installation-docker)
7. [References](#references)

# Overview <a name="overview"></a>

The **Brewery Data Ingestion and Enrichment Tool** is designed to collect, transform and store data from the [Open Brewery DB API](https://www.openbrewerydb.org/), following the [medallion architecture](https://www.databricks.com/glossary/medallion-architecture). This tool is built using the ```Python programming language``` and leverages ```PySpark``` for distributed data processing.

<img align="left" width="400" src="/images/brewery-pipeline.png" alt="brewery-pipeline"/>

The tool operates in a modular fashion, where we can run each step of the pipeline via *command line interface* (CLI). The user may choose to only run the *ingestion* of the data into the ```bronze``` storage, or they may choose to run the *enricher* to generate the ```silver``` and ```gold``` datasets from the last successful data ingestion. One last option would to just use the tool to run the entire data processing pipeline.

The tool stores the data based on the UTC timestamp at which the API data request took place. This gives the user the advantage of checking out the data at different points in time and compare versions for all three stages of the medallion structure. Furthermore, an optional feature provided by the tool is the integration with **Docker**. Details on how to run this tool with docker may be found in the [Docker](#installation-docker) section. However, the user has always the options to just install the tool directly on their machine and run it from there. Details on this installation are further detailed in the [Virtual Environment](#installation-virtual-environment) section.

With respect to logging, the tool stores information about each step of the data pipeline and allows the user to check on what is meaningful to them. Error handling is taken care on all steps as well, but particularly during ingestion, where it retries a few extra times in case of unsuccessful requests. A test suite was also created and may be run after the first full pipeline run is completed, since it checks for the quality of the data being created in all three storages (bronze, silver, and gold).

Finally, the dependencies for this tool are:

- Python 3.10+
- Click 8.0
- PySpark 3.5.2
- Requests 2.32.3
- pytest 7.0.0
- [optional] Docker Engine

# Data Ingestion <a name="data-ingestion"></a>

The data ingestion operation has the purpose of requesting the data from the API server and then creating the bronze medallion data storage. It does it by going through the following steps:

- depending on the number of data points requested per page, the tool calculates the maximum number of pages necessary to get the entire API dataset.
- it iterates through the requests, by starting at page 1 all the way to the maximum number of pages:
   - if a request fails, the tool stores the requested item in a file named ```failed_requests.raw``` for future processing.
   - the successful requests will get stored in a file named ```data.raw```.
   - both files can be read via Python's ```json``` module.
- the pipeline now runs a data quality step which is focused on checking if the number of successfully stored data points is the same as the number of data points available, as reported by the API server.
- the ingestion process finally checks the dataset ```failed_requests.raw``` to see if there are remaining items to be processed. If there are, the tool retries requesting them a specified number of times (default value of 5).
- the success or failure of the ingestion pipeline is dictated by the outcome of the previous two steps.

# Data Enrichment <a name="data-enrichment"></a>

The data enrichment operation has the purpose of processing the bronze medallion data and create both the silver and gold medallion data storages. It can be broken into two steps:

- creation of the silver medallion data storage
   - loads the latest bronze medallion dataset.
   - for each column in that dataset it trims the whitespaces in the beginning and ending of each value (all columns are of string type in the bronze stage).
   - changes the data types for the *latitude* and *longitude* columns from string to double.
   - it checks the brewery types from the incoming data and checks if they are in the list provided by the API.
   - selects the columns of interest, in a chosen order.
   - finally it partitions the data by country and stores it.
- creation of the gold medallion data storage
   - loads the latest silver medallion dataset.
   - groups by *country* and *brewery_type* and creates a *brewery_count* column
   - orders the dataset *country* and *brewery_type*.
   - since the datasets are not that big (even for countries like the United States) we make a repartition of size 1 to reduce the number of files generated.

# Error Handling and Logging <a name="error-handling-and-logging"></a>

Throughout the code used for the development of this tool you will notice logging events (information or error) at critical points. The purpose is to alert the user of what is happening as the data is getting processed. This is all performed using Python's ```logging``` module. There are two main files that will get created: ```data-pipeline/logs/breweries_info.log.jsonl``` and ```data-pipeline/logs/breweries_error.log.jsonl```

With respect to error handling, focus was given to the ingestion part of the pipeline. While requesting data from the API server, we may run into communication issues that will lead to failed requests. If that occurs for some given request item, we store them into a file to let the tool know that not all items were correctly processed. Once the tool completes the ingestion by going through all of the requests, it checks the file containing the possible failed items. If that file is empty, then the ingestion process is concluded. Otherwise, it will go through each of the failed items and retry them a specified number of times (default set is 5).

# Testing <a name="testing"></a>

This tool supports testing using the ```pytest``` module. However, currently this can only be done easily by installing the tool via virtual environment. Please refer to the [Virtual Environment](#installation-virtual-environment) section of the installation. It is important to emphasise that for the test suite to have a chance at completing all tests, a full pipeline run must be performed first since it validates the ingestion and the enrichment steps of the data process.

This tool currently has 3 sets of tests:
- API: has the purpose of testing the class *APITools*.
   - tests the functionality of obtaining the maximum page from the API to make sure the logic is working as intended.
   - tests the retrieval of data for the first page and makes sure that the size of the data is as expected.
- Ingester: has the purpose of testing the ingestion pipeline functionality
   - tests that the *Ingester* class is well integrated with the *APITools* class when performing the retrieval of one page of data.
- Enriched Data: has the purpose of run data quality checks on the generated data (bronze, silver, gold).
   - bronze
      - checks that the number of points of the bronze storage is the same as the number of data points reported by the API.
      - checks that the dataset contains the correct number of columns.
   - silver
      - checks that data count is close to the total number of points reported by the API, and that it has the correct number of columns.
      - checks that the columns *latitude* and *longitude* have a different data type.
   - gold
      - since we now have a rolled up dataset, we check for the reduced number of data points as well as the reduced number of columns.
      - check that the aggregated sum of datapoints passes the same test as the silver dataset.

These tests are all executed by [GitHub Actions](https://docs.github.com/en/actions) when a push is made to main to ensure that the data generated has the above quality requirements.

*Remark: you can run the tests using the Docker containers, but as of right now you would have to interactively run the container and then run the tests from within them.*

# Installation <a name="installation"></a>

## Virtual Environment <a name="installation-virtual-environment"></a>

In this section we assume that you have Python installed as well as the ```data-pipeline``` repository locally in your machine. We are going to show the install steps for Python's ```venv``` module. The steps for other virtual environment modules are similar.

The first step will be to change directories and go within the repository root, where you may run the following three commands sequentially:

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -e .[test]
```

Once they are complete you can confirm that the installation of the tool was successful by running either/both of the following commands (assuming you are still with your virtual environment activated):

```bash
breweries --help
```

```bash
breweries --version
```

The first command will output:

```bash
Usage: breweries [OPTIONS]

Options:
  -v, --version         Return version number.
  -ri, --run-ingestion  Run the ingestion pipeline.
  -re, --run-enricher   Run the enricher pipeline.
  --run-all             Run the end-to-end data pipeline.
  --help                Show this message and exit.
```

while the second command will output ```1.0.0```. By following these installation steps you will be able to run the tests using the ```pytest``` module.

Finally, if you are interested in running the full pipeline (ingestion and enrichment), make sure your virtual environment is activated and run the following command:

```bash
breweries --run-all
```

## Docker <a name="installation-docker"></a>

This section aims to explain how to run the tool via Docker. It assumes you have Docker installed as well as the repository pulled locally in your machine. For this example we are only interested in creating a Docker container that will run the full pipeline, from ingestion to enrichment, generating the three data storages of the medallion structure.

The first step would be to put the ```Dockerfile``` alongside the repository folder, ```data-pipeline```. The ```Dockerfile``` is contained within the ```configuration``` folder of the repository. The structure of the working directory would look as follows:

```bash
.
├── data-pipeline
└── Dockerfile
```

Now we can build the image by running the command below:

```bash
sudo docker build -t breweries-pipeline .
```

Once the image has finished building, we can run a container off of this image with the following command:

```bash
sudo docker run --name container-breweries-pipeline -v ./data:/home/ubuntu/data-pipeline/data -v ./logs:/home/ubuntu/data-pipeline/logs breweries-pipeline
```

Notice that in the command used to create the container, we are linking the directories ```data```  and ```logs``` to the container so we can persist the information that is being generated from within the container. After running the above command the following directory tree would show up:

```bash
.
├── data
│   ├── bronze
│   ├── gold
│   └── silver
├── data-pipeline
│   ├── configuration
│   ├── data
│   ├── logs
│   ├── README.md
│   ├── setup.py
│   ├── src
│   └── tests
├── Dockerfile
└── logs
    ├── breweries_error.log.jsonl
    └── breweries_info.log.jsonl
```

Let's finish this session by noticing how the ```data``` directory contains the three medallion storages, all of them with the same UTC timestamp subdirectory since they are all related to each other. Furthermore, within the ```silver``` medallion storage you will notice how the data is partitioned by location, in particular the country column of the API dataset.

```bash
data
├── bronze
│   └── 1726528757
│       ├── data.raw
│       └── failed_requests.raw
├── gold
│   └── 1726528757
│       ├── part-00000-0a345e91-fde3-4b3f-b4a2-1622e5fb694c-c000.snappy.parquet
│       └── _SUCCESS
└── silver
    └── 1726528757
        ├── country=Austria
        ├── country=England
        ├── country=France
        ├── country=Germany
        ├── country=Ireland
        ├── country=Isle of Man
        ├── country=Poland
        ├── country=Portugal
        ├── country=Scotland
        ├── country=Singapore
        ├── country=South Korea
        ├── country=Sweden
        ├── country=United States
        └── _SUCCESS
```

If we were to run the created container once again, a new UTC timestamp subdirectory would be created for each of the three storages:

```bash
data
├── bronze
│   ├── 1726528757
│   └── 1726529825
├── gold
│   ├── 1726528757
│   └── 1726529825
└── silver
    ├── 1726528757
    └── 1726529825
```

This is powerful because it allows you to revert back to older versions of the dataset in case of spotted issues or just to have a historical view of the data.

# References <a name="references"></a>

1) [Open Brewery DB](https://www.openbrewerydb.org/)
2) [Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)
3) Package dependencies: [PySpark](https://spark.apache.org/docs/latest/api/python/index.html), [pytest](https://docs.pytest.org/en/stable/), [Click](https://click.palletsprojects.com/en/8.1.x/), [Requests](https://requests.readthedocs.io/en/latest/).
4) [venv - Creation of virtual environments](https://docs.python.org/3/library/venv.html)
5) [GitHub Actions](https://docs.github.com/en/actions)
