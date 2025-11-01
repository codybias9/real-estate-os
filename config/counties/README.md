# County Configurations

This directory contains market-specific configuration files for different counties across the United States.

## Purpose

Each configuration file provides:
- Market demographics and statistics
- Scraping parameters for web crawlers
- County assessor information
- Data source priorities
- Market-specific filters and criteria
- Scoring adjustments for ML models
- Target neighborhoods with score multipliers
- Market notes and insights

## File Format

Configurations are in YAML format with the following structure:

```yaml
county_info:
  name: "County Name"
  state: "ST"
  state_full: "State Full Name"
  fips_code: "12345"
  population: 1000000
  median_home_price: 500000
  key_cities:
    - "City 1"
    - "City 2"

scrape_params:
  state: "ST"
  city: "City-Name"
  max_pages: 20
  rate_limit_delay: 2
  headless: true

assessor:
  name: "County Assessor Name"
  website: "https://..."
  parcel_url: "https://..."
  api_endpoint: null
  requires_selenium: true

data_sources:
  primary:
    - name: "Source Name"
      priority: 1
      spider: "spider_name"

filters:
  min_price: 100000
  max_price: 1000000
  property_types: ["Single Family", "Condo"]
  min_bedrooms: 2
  min_bathrooms: 1.5

scoring_adjustments:
  market_heat: 1.15
  appreciation_rate: 0.08
  days_on_market_target: 45

target_neighborhoods:
  - name: "Neighborhood Name"
    zip_codes: ["12345", "12346"]
    score_multiplier: 1.20

notes: |
  Market-specific insights and notes.
```

## Available Markets

### West Coast
- **Clark County, NV** (Las Vegas) - `clark_nv.yaml`
- **Maricopa County, AZ** (Phoenix) - `maricopa_az.yaml`
- **San Diego County, CA** (San Diego) - `san_diego_ca.yaml`
- **Orange County, CA** (Orange County) - `orange_ca.yaml`
- **King County, WA** (Seattle) - `king_wa.yaml`

### Texas
- **Harris County, TX** (Houston) - `harris_tx.yaml`
- **Travis County, TX** (Austin) - `travis_tx.yaml`

### Southeast
- **Miami-Dade County, FL** (Miami) - `miami_dade_fl.yaml`

### Midwest
- **Cook County, IL** (Chicago) - `cook_il.yaml`

## Usage

### In Spiders

```python
from pathlib import Path
import yaml

# Load county config
config_path = Path(__file__).parents[5] / 'config' / 'counties' / 'clark_nv.yaml'
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Access configuration
state = config['scrape_params']['state']
max_pages = config['scrape_params']['max_pages']
```

### In Airflow DAGs

```python
# Pass county as parameter
'county': 'clark_nv'

# DAG will load config file and pass parameters to scraper
```

## Adding New Markets

To add a new market:

1. Create a new YAML file: `{county}_{state}.yaml`
2. Follow the structure shown above
3. Research market-specific data:
   - Median home prices (Zillow, Redfin)
   - Appreciation rates (local MLS)
   - Target neighborhoods (local knowledge)
   - County assessor website and data access
4. Set appropriate scoring adjustments
5. Test scraper with the new configuration

## Scoring Adjustments

### market_heat
Multiplier for overall market conditions:
- `< 1.0` - Cooling/slow market
- `1.0` - Neutral market
- `> 1.0` - Hot/fast market

### appreciation_rate
Expected annual appreciation (as decimal):
- `0.04` - 4% per year (slow)
- `0.06-0.08` - 6-8% per year (moderate)
- `0.10+` - 10%+ per year (fast)

### days_on_market_target
Average days a property stays on the market:
- `< 30` - Very hot market
- `30-60` - Hot to moderate market
- `> 60` - Slower market

### score_multiplier (neighborhoods)
Neighborhood-specific multiplier:
- `1.0` - Average neighborhood
- `1.1-1.2` - Above average (good schools, amenities)
- `1.2-1.3` - Highly desirable
- `1.3+` - Premium/luxury areas

## Data Sources

Current supported sources:
- **FSBO.com** - For-sale-by-owner listings
- **ForSaleByOwner.com** - Alternative FSBO site
- **Craigslist** - Local classifieds

Planned sources:
- Zillow API (when available)
- Redfin scraping
- Local MLS feeds (with authorization)

## Notes

- All prices in USD
- Population data from US Census Bureau
- FIPS codes for county identification
- Configurations should be updated annually with market data
- Test scraping in staging before production deployment
