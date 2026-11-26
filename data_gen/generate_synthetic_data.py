
from pathlib import Path

from utilities.config import (
    load_config,
    initialize_random_generators
)

from utilities.validation import (
    validate_required_columns,
    validate_not_null,
    validate_unique,
    validate_foreign_key,
    validate_non_negative
)

from generators.reference_data import (
    generate_branches,
    generate_advisors,
    generate_securities
)

from generators.client_data import (
    generate_households,
    generate_clients
)

from generators.financial_data import (
    generate_accounts,
    generate_account_owners,
    generate_holdings,
    generate_transactions
)

from generators.crm_data import (
    generate_crm_contacts,
    generate_crm_interactions
)

from generators.source_data import (
    generate_core_customers,
    generate_truth_client_map
)


def save_dataframes(dataframes, output_directory):
    """
    Save each DataFrame as a Parquet file in its own table directory.
    """
    output_directory = Path(output_directory)

    for table_name, dataframe in dataframes.items():

        # Create a separate directory for each generated table.
        table_directory = output_directory / table_name
        table_directory.mkdir(parents=True, exist_ok=True)

        # Save the DataFrame without its pandas index.
        output_path = table_directory / f"{table_name}.parquet"
        dataframe.to_parquet(output_path, index=False)

        print(
            f"Saved {table_name}: "
            f"{len(dataframe):,} rows -> {output_path}"
        )


def validate_generated_data(
    branches,
    advisors,
    securities,
    golden_clients,
    accounts,
    account_owners,
    holdings,
    transactions,
    crm_contacts,
    crm_interactions,
    core_customers,
    truth_client_map
):
    """
    Validate required fields, unique identifiers, and relationships
    across the generated datasets.
    """

    # Check that the expected primary-key columns exist.
    # dataframe_name, (dataframe, columns)
    required_columns = {
        "branches": (branches, ["branch_id"]),
        "advisors": (advisors, ["advisor_id", "branch_id"]),
        "securities": (securities, ["security_id"]),
        "golden_clients": (golden_clients, ["golden_client_id"]),
        "accounts": (
            accounts,
            ["account_id", "golden_client_id", "advisor_id"]
        ),
        "account_owners": (
            account_owners,
            ["account_id", "golden_client_id", "ownership_role"]
        ),
        "holdings": (
            holdings,
            ["account_id", "security_id", "quantity", "price",
             "market_value", "cost_basis"]
        ),
        "transactions": (
            transactions,
            ["txn_id", "account_id", "security_id", "amount"]
        ),
        "crm_contacts": (crm_contacts, ["contact_id"]),
        "crm_interactions": (
            crm_interactions,
            ["interaction_id", "contact_id"]
        ),
        "core_customers": (core_customers, ["customer_id"]),
        "truth_client_map": (
            truth_client_map,
            ["source_system", "source_id", "golden_client_id"]
        )
    }

    for dataframe_name, (dataframe, columns) in required_columns.items():
        validate_required_columns(
            dataframe,
            columns,
            dataframe_name
        )

    # Check that primary identifiers are present and unique.
    validate_not_null(branches, ["branch_id"], "branches")
    validate_unique(branches, "branch_id", "branches")

    validate_not_null(advisors, ["advisor_id", "branch_id"], "advisors")
    validate_unique(advisors, "advisor_id", "advisors")

    validate_not_null(securities, ["security_id"], "securities")
    validate_unique(securities, "security_id", "securities")

    validate_not_null(
        golden_clients,
        ["golden_client_id"],
        "golden_clients"
    )
    validate_unique(
        golden_clients,
        "golden_client_id",
        "golden_clients"
    )

    validate_not_null(accounts, ["account_id"], "accounts")
    validate_unique(accounts, "account_id", "accounts")

    validate_not_null(
        account_owners,
        ["account_id", "golden_client_id"],
        "account_owners"
    )

    validate_not_null(holdings, ["account_id", "security_id"], "holdings")

    validate_not_null(
        transactions,
        ["txn_id", "account_id"],
        "transactions"
    )
    validate_unique(transactions, "txn_id", "transactions")

    validate_not_null(crm_contacts, ["contact_id"], "crm_contacts")
    validate_unique(crm_contacts, "contact_id", "crm_contacts")

    validate_not_null(
        crm_interactions,
        ["interaction_id", "contact_id"],
        "crm_interactions"
    )
    validate_unique(
        crm_interactions,
        "interaction_id",
        "crm_interactions"
    )

    validate_not_null(
        core_customers,
        ["customer_id"],
        "core_customers"
    )
    validate_unique(
        core_customers,
        "customer_id",
        "core_customers"
    )

    validate_not_null(
        truth_client_map,
        ["source_system", "source_id", "golden_client_id"],
        "truth_client_map"
    )

    # validate foreign-key relationships between generated datasets
    validate_foreign_key(
        advisors, "branch_id",
        branches, "branch_id",
        "advisors"
    )

    validate_foreign_key(
        accounts, "golden_client_id",
        golden_clients, "golden_client_id",
        "accounts"
    )

    validate_foreign_key(
        accounts, "advisor_id",
        advisors, "advisor_id",
        "accounts"
    )

    validate_foreign_key(
        account_owners, "account_id",
        accounts, "account_id",
        "account_owners"
    )

    validate_foreign_key(
        account_owners, "golden_client_id",
        golden_clients, "golden_client_id",
        "account_owners"
    )

    validate_foreign_key(
        holdings, "account_id",
        accounts, "account_id",
        "holdings"
    )

    validate_foreign_key(
        holdings, "security_id",
        securities, "security_id",
        "holdings"
    )

    validate_foreign_key(
        transactions, "account_id",
        accounts, "account_id",
        "transactions"
    )

    # Security IDs are optional for cash transactions.
    validate_foreign_key(
        transactions, "security_id",
        securities, "security_id",
        "transactions"
    )

    # Orphan CRM prospects can have a null advisor_id.
    validate_foreign_key(
        crm_contacts, "advisor_id",
        advisors, "advisor_id",
        "crm_contacts"
    )

    validate_foreign_key(
        crm_interactions, "contact_id",
        crm_contacts, "contact_id",
        "crm_interactions"
    )

    # Check that holding values are non-negative.
    # Transaction amounts are excluded because negative amounts
    # represent valid cash outflows.
    validate_non_negative(
        holdings,
        ["quantity", "price", "market_value", "cost_basis"],
        "holdings"
    )

    print("All generated-data validation checks passed.")


def generate_synthetic_data(config_path):
    """
    This generates the synthetic data, validates, and saves the data.
    """

    # 1. Load configuration and initialize random generators

    config = load_config(config_path)

    # initializes all random_generators
    rngs = initialize_random_generators(
        config["synthetic_data"]["seed"]
    )

    print("Configuration loaded.")
    print("Random generators initialized.")

    # 2. Generate reference data

    branches = generate_branches(config, rngs)

    advisors = generate_advisors(
        config,
        branches,
        rngs
    )

    securities = generate_securities(config, rngs)

    print("Reference data generated.")

    # 3. Generate the clean golden population

    households = generate_households(config, rngs)

    golden_clients = generate_clients(
        config,
        households,
        advisors,
        rngs
    )

    print("Golden clients and households generated.")

    # 4. Generate financial data

    accounts = generate_accounts(
        config,
        golden_clients,
        rngs
    )

    account_owners = generate_account_owners(
        config,
        accounts,
        golden_clients,
        households,
        rngs
    )

    holdings = generate_holdings(
        config,
        accounts,
        securities,
        rngs
    )

    transactions = generate_transactions(
        config,
        accounts,
        securities,
        rngs
    )

    print("Financial data generated.")

    # 5. Generate CRM source data

    # CRM contact generation also applies the configured CRM noise.
    crm_contacts = generate_crm_contacts(
        config,
        golden_clients,
        rngs
    )

    crm_interactions = generate_crm_interactions(
        crm_contacts,
        rngs
    )

    print("CRM data generated.")

    # 6. Generate Core source data

    core_customers = generate_core_customers(
        golden_clients,
        rngs
    )

    print("Core customer data generated.")

    # 7. Generate the private ground-truth mapping

    truth_client_map = generate_truth_client_map(
        crm_contacts,
        core_customers
    )

    print("Ground-truth mapping generated.")

    # 8. Validate generated data before preparing source outputs

    validate_generated_data(
        branches,
        advisors,
        securities,
        golden_clients,
        accounts,
        account_owners,
        holdings,
        transactions,
        crm_contacts,
        crm_interactions,
        core_customers,
        truth_client_map
    )

    # 9. Prepare source-aligned DataFrames

    # Map each golden client ID to its separate Core customer ID.
    customer_id_map = dict(
        zip(
            core_customers["golden_client_id"],
            core_customers["customer_id"]
        )
    )

    # Convert internal golden client references into source-system IDs.
    source_account_owners = account_owners.copy()
    source_account_owners["customer_id"] = (
        source_account_owners["golden_client_id"].map(customer_id_map)
    )

    # Remove internal identifiers that do not belong in the source extracts.
    source_account_owners = source_account_owners.drop(
        columns=["golden_client_id"]
    )

    source_accounts = accounts.drop(
        columns=["golden_client_id", "account_aum"]
    )

    source_crm_contacts = crm_contacts.drop(
        columns=["golden_client_id"]
    )

    source_core_customers = core_customers.drop(
        columns=["golden_client_id"]
    )


    # 10. Organize source and private datasets

    source_data = {
        "ref_branch": branches,
        "ref_advisor": advisors,
        "cust_security_master": securities,
        "acct_account": source_accounts,
        "acct_account_owner": source_account_owners,
        "cust_holding_snapshot": holdings,
        "txn_ledger": transactions,
        "crm_contact": source_crm_contacts,
        "crm_interaction": crm_interactions,
        "acct_customer": source_core_customers
    }

    # Keep the clean population and truth mapping separate from
    # the source-system extracts used by the Bronze ingestion process.
    private_data = {
        "golden_clients": golden_clients,
        "households": households,
        "truth_client_map": truth_client_map
    }

    generated_data = {
        **source_data,
        **private_data
    }

    # ---------------------------------------------------------
    # 11. Save generated datasets
    # ---------------------------------------------------------

    landing_zone = config["storage"]["landing_zone"]

    save_dataframes(
        source_data,
        Path(landing_zone) / "source_data"
    )

    save_dataframes(
        private_data,
        Path(landing_zone) / "_private"
    )

    print("Synthetic data generation completed successfully.")

    return generated_data


# -------------------------------------------------------------
# 12. Script entry point
# -------------------------------------------------------------

if __name__ == "__main__":

    # Locate dev.yml relative to this Python file.
    project_directory = Path(__file__).resolve().parent
    config_path = project_directory / "config" / "dev.yml"

    generate_synthetic_data(config_path)
