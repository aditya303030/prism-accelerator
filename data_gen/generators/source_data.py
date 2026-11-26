import pandas as pd

def generate_core_customers(golden_clients, rngs):
    fake = rngs["faker"]

    if golden_clients.empty:
        raise ValueError("cannot generate core customers without clients")
    
    customers = []

    # generate 1 core customer record for every golden client
    for number, (_, client) in enumerate(golden_clients.iterrows(), start=1):
        # assign a core-specific id instead of reusing the golden client ID
        customer_id = f"CORE{number:08d}"

        # create full name of the client's name fields 
        full_name = " ".join([
            client["first_name"],
            client["middle_name"],
            client["last_name"]
        ])

        # Generate the last-modified timestamp after the client's onboarding.
        updated_at = fake.date_time_between(
            start_date=client["onboarding_date"],
            end_date="now"
        )

        # create the customer and append to customers list
        customer = {
            "customer_id": customer_id,
            "golden_client_id": client["golden_client_id"],
            "full_name": full_name,
            "dob": client["dob"],
            "tax_id_hash": client["tax_id_hash"],
            "email": client["email"],
            "mobile": client["phone"],
            "mailing_address": client["address_line1"],
            "city": client["city"],
            "state": client["state"],
            "zip": client["zip"],
            "kyc_status": client["kyc_status"],
            "risk_profile": client["risk_profile"],
            "onboarding_date": client["onboarding_date"],
            "updated_at": updated_at
        }

        customers.append(customer)
    
    # create a dataframe using the list and return it
    customers_df = pd.DataFrame(customers)

    return customers_df

# this will create a dataframe that will have a source_system, source_id 
# and the golden_client that the source is linked to
# generate_truth_client_map() creates a ground-truth mapping between source-system 
# records (CRM and Core) and their original golden_client_id. It excludes orphan CRM prospects 
# that do not have a corresponding golden client.

# Structure: Returns a Pandas DataFrame with three columns: source_system, source_id, 
# and golden_client_id. This mapping is kept separate from Bronze source data and used 
# to evaluate the accuracy of the Entity Resolution pipeline.
def generate_truth_client_map(crm_contacts, acct_customers):

    truth_records = []

    # map each CRM contact to its original golden client
    for _, contact in crm_contacts.iterrows():

        # Skip orphan CRM prospects because they do not correspond
        # to an existing golden client.
        if pd.isna(contact["golden_client_id"]):
            continue

        # this will store the CRM source identifier and its known golden client ID.
        # Multiple CRM contacts can map to the same golden client if duplicates exist.
        truth_records.append({
            "source_system": "CRM",
            "source_id": contact["contact_id"],
            "golden_client_id": contact["golden_client_id"]
        })

    # Map each Core customer record to its original golden client.
    for _, customer in acct_customers.iterrows():

        # Store the Core source identifier and its known golden client ID.
        truth_records.append({
            "source_system": "CORE_ACCT",
            "source_id": customer["customer_id"],
            "golden_client_id": customer["golden_client_id"]
        })

    # Convert the collected source-to-golden-client mappings into a DataFrame.
    truth_client_map = pd.DataFrame(
        truth_records,
        columns=[
            "source_system",
            "source_id",
            "golden_client_id"
        ]
    )

    # Return the ground-truth mapping used to evaluate entity resolution.
    return truth_client_map