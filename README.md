# Target Scraper
## Overview
This scraper allows to get data from Target website and the data will be saved in a CSV file.


## Requirements
- Python 3.x
- Scrapy


## Installation
Install Python if you haven't already: Python Installation Guide
Install required Python packages: `pip install -r requirements.txt`

## Usage
- Clone or download the script.
- Open a terminal and navigate to the directory where the script is located.
- Put the category urls in `catalog_urls.txt` file (one per line).
- Specify the output file name using the -o parameter.
- Run the script using Python: `scrapy crawl target` this will create a CSV file with the scraped data `output.csv`.
