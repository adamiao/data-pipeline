from src.breweries import __version__
from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="breweries",
    version=__version__,
    author="Alexandre Damião",
    description="This is a brewery data ingestion and processing tool.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src", exclude=["configuration", "images", "logs", "tests", "data"]),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX",
    ],
    python_requires=">=3.10",
    install_requires=[
        "click == 8.0",
        "pyspark == 3.5.2",
        "requests == 2.32.3",
    ],
    extras_require={
        "test": [
            "pytest >= 7.0.0",
        ],
    },
    entry_points={
        "console_scripts": ["breweries=breweries.cli:main"]
    }
)
