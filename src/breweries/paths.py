from pathlib import Path


# ---------------
# USER DETERMINED PATHS
# ---------------

DATA_BASE_PATH = Path(__file__).parents[2].joinpath("data/")

# ---------------
# DEPENDENT PATHS
# ---------------

PATH_DATA_BRONZE = DATA_BASE_PATH.joinpath("bronze/")
PATH_DATA_SILVER = DATA_BASE_PATH.joinpath("silver/")
PATH_DATA_GOLD = DATA_BASE_PATH.joinpath("gold/")
