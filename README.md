# schleflix
Download script for SchleFlix (SchleFaZ Mediathek).
This script will download all SchleFaZ movies available in the Mediathek including the cover image files.
You can run this script regularly to add new movies as they are released. 

## Installation and Usage

The following instructions are for Linux systems, but you may also run this script on Windows.

1. Download source code
    1. `git clone https://github.com/simon-wessel/schleflix.git`
    2. `cd schleflix`
1. (Optional) Install and activate virtual environment
    1. `python3 -m venv env`
    1. `source env/bin/activate
1. Download requirements
    1. `pip3 install -r requirements.txt`
3. Set up .env file
    1. `cp .env.example .env`
    1. Make changes according to your wishes in the .env file
        1. Use `YDL_QUIET_MODE=False` if you want to see more information and progress on the console
        1. Set `MAX_WORKERS` to configure how many movies will be downloaded at the same time
4. Run script
    1. `python3 schlefaz.py`
    1. Movies will be downloaded to the subdirectory `output` by default settings
