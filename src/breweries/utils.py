import os
from pathlib import Path
from typing import Optional


def create_utc_timestamp_subdirectory(parent_directory: Path, rounded_utc_timestamp: int) -> Path:
    """
    Creates a subdirectory in a given parent directory with the UTC timestamp as its name.
    :param parent_directory: [pathlib.Path] under which it is desired to build the subdirectory with the UTC timestamp
                             name.
    :param rounded_utc_timestamp: [int] rounded value for the UTC timestamp.
    :return: [pathlib.Path] with the UTC timestamp name
    """
    output_filepath = parent_directory.joinpath(f"{rounded_utc_timestamp}/")
    output_filepath.mkdir(parents=True, exist_ok=True)
    return output_filepath


def get_most_recent_directory(directory_path: Path) -> Optional[Path]:
    """
    Return the most recently modified/created directory within an input directory (modified: Unix/ created: Windows).
    :param directory_path: [pathlib.Path] parent directory which this function will be iterating on.
    :return: [Optional[pathlib.Path]] the most recent directory that was created or modified (depends on the system)
    """
    sorted_directory = sorted(directory_path.iterdir(), key=os.path.getctime, reverse=False)
    while sorted_directory:
        directory_item = sorted_directory.pop()
        if directory_item.is_dir():
            return directory_item
