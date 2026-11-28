import pandas as pd
import string

def generate_branches(config, rngs):
    fake = rngs["faker"]

    # gets branch count from the dev.yml file
    branch_count = config["synthetic_data"]["scale"]["branches"]

    branches = []

    for number in range(branch_count):
        # generate a branch_id
        branch_id = f"BR{number + 1:03d}"

        # creates a fake branch
        branch = {
            "branch_id": branch_id,
            "branch_name": f"{fake.city()} Wealth Management",
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip_code": fake.zipcode()
        }

        branches.append(branch)

    return pd.DataFrame(branches)


def generate_advisors(config, branches, rngs):

    fake = rngs["faker"]
    rng = rngs["python"]

    advisor_count = config["synthetic_data"]["scale"]["advisors"]

    # advisors need branches
    if branches.empty:
        raise ValueError("Cannot generate advisors without branches")
    
    branch_ids = list(branches["branch_id"])

    employment_statuses = ["Active", "Active", "Active", "Inactive"]

    advisors = []

    for number in range(advisor_count):

        # create an advisor_id
        advisor_id = f"ADV{number + 1:03d}"

        first_name = fake.first_name()
        last_name = fake.last_name()

        advisor = {
            "advisor_id": advisor_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": (
                f"{first_name.lower}."
                f"{last_name.lower()}@example.com"
            ),
            # assign a random branch to id
            "branch_id": rng.choice(branch_ids),
            "hire_date": fake.date_between(
                start_date="-30y",
                end_date="today"
            ),
            "employment_status": rng.choice(employment_statuses)
        }

        advisors.append(advisor)
    
    return pd.DataFrame(advisors)

# generate a synthetic reference dataset of investment securities
def generate_securities(config, rngs):
    fake = rngs["faker"]
    rng = rngs["python"]

    security_count = config["synthetic_data"]["scale"]["securities"]

    # probability of each security belonging to a particular asset class
    asset_class_weights = {
        "Equity": 0.50,
        "Fixed Income": 0.30,
        "Cash": 0.05,
        "Alternatives": 0.15
    }

    asset_classes = list(asset_class_weights.keys()) # possible asset classes
    asset_weights = list(asset_class_weights.values()) # probability associated with each class

    # possible equity sectors
    equity_sectors = [
        "Technology",
        "Healthcare",
        "Financials",
        "Consumer Discretionary",
        "Consumer Staples",
        "Energy",
        "Industrials",
        "Materials",
        "Utilities",
        "Real Estate",
        "Communication Services"
    ]

    # security list and ticker tracker
    securities = [] # stores the dictionaries representing each generated security
    used_tickers = set() # tracks tickers already assigned

    currencies = ["USD", "EUR", "GBP", "CAD"]

    # generates the requested number of securities
    for number in range(security_count):
        security_id = f"SEC{number + 1:03d}"
        
        # generating a unique 4 letter uppercase ticker
        ticker = ""

        while not ticker or ticker in used_tickers:
            ticker = "".join(
                rng.choices(string.ascii_uppercase, k=4)
            )

        # add the tickers to the set of previously used tickers
        used_tickers.add(ticker)

        # randomly selecting an asset class using the defined probabilities. 
        # k=1 selects 1 item and [0] indexing selects that item from the list
        asset_class = rng.choices(
            asset_classes,
            weights=asset_weights,
            k=1
        )[0]

        # generating a random company name + Common Stock.
        if asset_class == "Equity":
            security_name = f"{fake.company()} Common Stock"
            # random equity sector assigned
            sector = rng.choice(equity_sectors)

        # Generate a fictional company + Bond.
        elif asset_class == "Fixed Income":
            security_name = f"{fake.company()} Bond"

            # Randomly classify the bond from the choices:
            # 1. Government, 2. Corporate, 3. Municipal
            sector = rng.choice([
                "Government",
                "Corporate",
                "Municipal"
            ])
        
        # generating a random company name + Money Market Fund.
        elif asset_class == "Cash":
            security_name = f"{fake.company()} Money Market Fund"
            # cash and equivalent securities use this sector
            sector = "Cash & Equivalents"

        # this generates a fictional alternative investment fund name
        else:
            security_name = f"{fake.company()} Alternative Fund"

            # Randomly classify the alternative investment.
            sector = rng.choice([
                "Private Equity",
                "Real Assets",
                "Hedge Funds",
                "Commodities"
            ])

        # this creates a dictionary containing all the attributes of this security generated above
        security = {
            "security_id": security_id,
            "ticker": ticker,
            "cusip": f"SYN{number + 1:06d}",
            "security_name": security_name,
            "asset_class": asset_class,
            "sector": sector,
            "currency": rng.choice(currencies)
        }

        # add the security record to the list.
        securities.append(security)
        
    return pd.DataFrame(securities)
