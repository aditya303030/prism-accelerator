import pandas as pd
from datetime import timedelta

def generate_accounts(config, golden_clients, rngs):
    fake = rngs["faker"]
    rng = rngs["python"]

    client_count = config["synthetic_data"]["scale"]["clients"]

    # clients can't be empty
    if golden_clients.empty:
        raise ValueError("Cannot generate accounts without clients.")

    # different account types, products, and account_statuses
    account_types = [
        "IRA",
        "ROTH_IRA",
        "TAXABLE",
        "TRUST"
    ]

    products = [
        "Advisory",
        "Brokerage",
        "Managed Portfolio"
    ]

    account_statuses = [
        "ACTIVE",
        "ACTIVE",
        "ACTIVE",
        "ACTIVE",
        "ACTIVE",
        "RESTRICTED",
        "CLOSED"
    ]

    accounts = []

    account_number = 1
    
    # for each client
    for _, client in golden_clients.iterrows():

        # generate between 1 and 5 accounts for each client.
        number_of_accounts = rng.randint(1, 5)

        # store all clients accounts in this list
        client_accounts = []

        # for each account
        for _ in range(number_of_accounts):
            account_type = rng.choice(account_types)
            product = rng.choice(products)
            status = rng.choice(account_statuses)

            open_date = fake.date_between(
                start_date=client["onboarding_date"],
                end_date="today"
            )

            account = {
                "account_id": f"ACCT{account_number:08d}",
                "golden_client_id": client["golden_client_id"],
                "account_type": account_type,
                "product": product,
                "open_date": open_date,
                "status": status,
                "currency": "USD",
                "advisor_id": client["advisor_id"]
            }

            client_accounts.append(account)

            account_number += 1

        # only the accounts that are not closed
        open_accounts = []

        for account in client_accounts:
            if account["status"] != "CLOSED":
                open_accounts.append(account)

        # making sure that every client has at least 1 account
        if not open_accounts:
            client_accounts[0]["status"] = "ACTIVE"
            open_accounts.append(client_accounts[0])

        # generating random weights for distributing the client's AUM
        # generating random numbers and taking percentage of each to assign a certain
        # percentage of AUM to each account 
        weights = []

        for _ in open_accounts:
            weights.append(rng.random())

        total_weight = sum(weights)

        target_aum = float(client["target_aum"])
        allocated_aum = 0

        # this distributes the AUM across the client's open accounts
        for number, account in enumerate(open_accounts):

            # this checks whether we are processing the last account
            if number == len(open_accounts) - 1:
                account_aum = round(target_aum - allocated_aum, 2)

            else:
                account_aum = round(target_aum * weights[number] / total_weight, 2)
                allocated_aum += account_aum

            account["account_aum"] = account_aum

        # Closed accounts receive no current AUM.
        for account in client_accounts:
            if account["status"] == "CLOSED":
                account["account_aum"] = 0.00

        accounts.extend(client_accounts)

    accounts_df = pd.DataFrame(accounts)

    return accounts_df


def generate_account_owners(config, accounts, golden_clients, households, rngs):

    rng = rngs["python"]

    joint_account_rate = config["synthetic_data"]["noise_rates"]["joint_accounts"]

    if accounts.empty:
        raise ValueError("Can't generate account ownsers without accounts")
    
    if golden_clients.empty:
        raise ValueError("Can't generate any accounts without clients")
    
    # mapping each client to their households
    # this will be a dictionary - {golden_client_id: household_id}
    client_households = {}

    for _,row in households.iterrows():
        client_households[row["golden_client_id"]] = row["household_id"]
    
    # group clients by households to find all clients that belong to a particulat household
    # structure: {household1:[1, 2, 3...], household2:[1, 3, 4...]...}
    household_members = {}

    for golden_client_id, household_id in client_households.items():
        # if household_id exists it returns it and then append to the end of the list
        # if it doesn't exist, then it will create household_id: [] and then append to the end of the list
        household_members.setdefault(household_id, []).append(golden_client_id)

    # identify the accounts aligible for joint ownership
    eligible_accounts = []

    for _, account in accounts.iterrows():
        # get primary owner from account (row inside accounts) and find the household_id for that primary_owner
        primary_owner = account["golden_client_id"]
        household_id = client_households[primary_owner]

        other_members = [
            client_id
            for client_id in household_members[household_id]
            if client_id != primary_owner
        ]

        # adding all other members
        # looping through each client id and adding them if they are not primary_owner
        other_members = []
        for client_id in household_members[household_id]:
            if client_id != primary_owner:
                other_members.append(client_id)
                
        # if there are other members, append their account to eligible_accounts
        if other_members:
            eligible_accounts.append(account["account_id"])
    
    # Select approx. 20% of all accounts to be joint ownership accounts (in dev.yml)
    account_owners = []

    joint_count = round(len(accounts) * joint_account_rate)
    # number of joint accounts cant be greater than the number of eligible accounts
    joint_count = min(joint_count, len(eligible_accounts))

    # randomly selecting account ids from eligible accounts to make joint accounts
    joint_account_ids = set(
        # from all eligible_accounts, select joint_count number of accounts
        rng.sample(eligible_accounts, joint_count)
    )

    account_owners = []

    # for each account get account_id and the primary_owner and append to account_owners
    for _, account in accounts.iterrows():
        account_id = account["account_id"]
        primary_owner = account["golden_client_id"]

        account_owners.append({
            "account_id": account_id,
            "golden_client_id": primary_owner,
            "ownership_role": "PRIMARY"
        })

        # add a second owner if account is a joint account
        # this is done by first getting a household_id liked to a primary owner, then looping over 
        # other client_ids in that household that are not the primary owner and randomly picking one of them
        if account_id in joint_account_ids:
            household_id = client_households[primary_owner]

            other_members = []
            for client_id in household_members[household_id]:
                if client_id!= primary_owner:
                    other_members.append(client_id)

            
            joint_owner = rng.choice(other_members)

            account_owners.append({
                "account_id": account_id,
                "golden_client_id": joint_owner,
                "ownership_role": "JOINT"
            })

    account_owners_df = pd.DataFrame(account_owners)

    return account_owners_df


def generate_holdings(config, accounts, securities, rngs):
    rng = rngs["python"]
    fake = rngs["faker"]

    if accounts.empty:
        raise ValueError("Cannot generate holdings without accounts")
    

    if securities.empty:
        raise ValueError("Cannot generate holdings without securities")
    
    security_ids = list(securities["security_id"])

    # Generate one snapshot date shared by all holdings.
    snapshot_date = fake.date_between(
        start_date="-30d",
        end_date="today"
    )

    # store all holdings in this
    holdings = []

    # for each account, get the account AUM, generate a random number of holdings for that account (between 5 and 40)
    # then select a sample of size min(number_of_holdings, len(security_ids)) from all security_ids 
    for _, account in accounts.iterrows():
        account_id = account["account_id"]
        account_aum = float(account["account_aum"])

        # generate between 5 and 40 holdings for each account.
        number_of_holdings = rng.randint(5, 40)

        # from the security_ids, select either num_of_holdings or len(security_ids) number of security_ids
        selected_securities = rng.sample(
            security_ids,
            min(number_of_holdings, len(security_ids))
        )

        # generates random weights for distributing account AUM.
        weights = []

        for _ in selected_securities:
            weights.append(rng.uniform(0.01, 1.0))

        total_weight = sum(weights)
        allocated_aum = 0

        # Loop through each selected security and its index.
        for number, security_id in enumerate(selected_securities):

            # Generate a random security price between $10 and $500.
            # Round the price to two decimal places.
            security_price = round(rng.uniform(10, 500), 2)

            # If the account has no AUM, the holding has no market value.
            if account_aum == 0:
                market_value = 0.00

            # For the last security, assign all remaining AUM.
            # This ensures that the total market value of the holdings
            # equals the account's AUM after rounding.
            elif number == len(selected_securities) - 1:
                market_value = round(
                    account_aum - allocated_aum,
                    2
                )

            # For every other security, distribute a portion of the
            # account's AUM based on its randomly generated weight.
            else:
                market_value = round(
                    account_aum * weights[number] / total_weight,
                    2
                )

                # Track the amount already allocated so the final
                # security can receive the remaining balance.
                allocated_aum += market_value

            # Calculate the quantity of the security held.
            # Quantity = market value divided by price per unit.
            quantity = market_value / security_price

            # Cost basis is modeled as a value near the current market value.
            cost_basis = round(
                market_value * rng.uniform(0.70, 1.10),
                2
            )

            holding = {
                "snapshot_date": snapshot_date,
                "account_id": account_id,
                "security_id": security_id,
                "quantity": quantity,
                "price": security_price,
                "market_value": market_value,
                "cost_basis": cost_basis
            }

            holdings.append(holding)

    holdings_df = pd.DataFrame(holdings)

    return holdings_df
    


def generate_transactions(config, accounts, securities, rngs):
    fake = rngs["faker"]
    rng = rngs["python"]

    # Make sure accounts and securities are available before generating transactions.
    if accounts.empty:
        raise ValueError("Cannot generate transactions without accounts.")

    if securities.empty:
        raise ValueError("Cannot generate transactions without securities.")

    # Store all security IDs so investment-related transactions can reference them.
    security_ids = list(securities["security_id"])

    # the types of transactions that can occur in an account
    transaction_types = [
        "BUY",
        "SELL",
        "DEPOSIT",
        "WITHDRAWAL",
        "DIVIDEND"
    ]

    # the channels through which transactions can take place
    channels = [
        "ONLINE",
        "ADVISOR",
        "PHONE",
        "BRANCH"
    ]

    transactions = []

    # Used to create a unique ID for every transaction.
    transaction_number = 1

    # Generate transactions separately for each account.
    for _, account in accounts.iterrows():

        account_id = account["account_id"]

        # Generate a random number of transactions between 5 and 30 for this account.
        number_of_transactions = rng.randint(5, 30)

        for _ in range(number_of_transactions):

            # Randomly select the type of transaction.
            txn_type = rng.choice(transaction_types)

            # Generate a trade date between the account's opening date and today.
            trade_date = fake.date_between(
                start_date=account["open_date"],
                end_date="today"
            )

            # Generate a settlement date 1–3 days after the trade date.
            settle_date = trade_date + timedelta(
                days=rng.randint(1, 3)
            )

            # Generate a random transaction amount between $100 and $10,000.
            amount = round(rng.uniform(100, 10000), 2)

            # BUY, SELL, and DIVIDEND transactions are associated with a security.
            # DEPOSIT and WITHDRAWAL transactions only affect the account's cash.
            if txn_type in ["BUY", "SELL", "DIVIDEND"]:
                security_id = rng.choice(security_ids)
            else:
                security_id = None

            # BUY and WITHDRAWAL transactions reduce the account's cash balance.
            # Represent these cash outflows with negative amounts.
            if txn_type in ["BUY", "WITHDRAWAL"]:
                amount = -amount

            # BUY and SELL transactions involve a quantity of securities.
            # Generate a positive quantity for these transactions.
            if txn_type in ["BUY", "SELL"]:
                quantity = round(rng.uniform(1, 100), 4)
            else:
                # Other transaction types do not have a security quantity.
                quantity = 0.0

            # Combine the generated values into a transaction record.
            transaction = {
                "txn_id": f"TXN{transaction_number:010d}",
                "account_id": account_id,
                "trade_date": trade_date,
                "settle_date": settle_date,
                "txn_type": txn_type,
                "security_id": security_id,
                "quantity": quantity,
                "amount": amount,
                "channel": rng.choice(channels)
            }

            # Add the transaction record to the overall list.
            transactions.append(transaction)

            # Increment the counter so the next transaction receives a unique ID.
            transaction_number += 1

    # Convert the list of transaction records into a DataFrame.
    transactions_df = pd.DataFrame(transactions)

    return transactions_df