import pandas as pd

from utilities.noise import (
    apply_nicknames,
    introduce_typos,
    introduce_missing_values,
    introduce_stale_contact_details,
    introduce_duplicates
)


def generate_crm_contacts(config, golden_clients, rngs):
    rng = rngs["python"]
    fake = rngs["faker"]

    noise_rates = config["synthetic_data"]["noise_rates"]

    if golden_clients.empty:
        raise ValueError("can't generate CRM contacts without any clients")
    
    contacts = []

    # this generates one initial CRM contact record for each golden client
    # loops through every row and returns number starting at 1 (start = 1)
    # then it returns row's data as a tuple unpacked (0, first_row), (1, second_row)
    # _ means we dont need the DataFrame index
    for number, (_, client) in enumerate(golden_clients.iterrows(), start=1):

        # Assign a CRM-specific ID instead of reusing the golden client ID.
        contact_id = f"CRM{number:08d}"

        # Store DOB as a string because the CRM source contains raw date strings
        # Randomly vary the format to simulate inconsistent source data
        dob = client["dob"].strftime(
            rng.choice(["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"])
        )

        # Generate the date the contact was originally created in the CRM.
        created_at = fake.date_time_between(
            start_date="-10y",
            end_date="now"
        )

        # Generate an update timestamp that occurs on or after creation.
        updated_at = fake.date_time_between(
            start_date=created_at,
            end_date="now"
        )

        # Build the CRM record using the golden client's initial information.
        contact = {
            "contact_id": contact_id,
            "golden_client_id": client["golden_client_id"],
            "first_name": client["first_name"],
            "middle_name": client["middle_name"],
            "last_name": client["last_name"],
            "dob": dob,
            "email": client["email"],
            "phone": client["phone"],
            "address_line1": client["address_line1"],
            "city": client["city"],
            "state": client["state"],
            "zip": client["zip"],
            "segment": client["segment"],
            "advisor_id": client["advisor_id"],
            "created_at": created_at,
            "updated_at": updated_at
        }

        contacts.append(contact)

    contacts_df = pd.DataFrame(contacts)

    # now generate older contact details so some CRM records can contain
    # outdated addresses or email addresses instead of current information for some data quality anomalies
    previous_contact_details = golden_clients[
        ["golden_client_id"]
    ].copy()

    previous_contact_details["address_line1"] = [
        fake.street_address()
        for _ in range(len(golden_clients))
    ]

    previous_contact_details["email"] = [
        fake.email()
        for _ in range(len(golden_clients))
    ]

    # Replace current addresses or emails with older values for some contacts.
    contacts_df = introduce_stale_contact_details(
        contacts_df,
        previous_contact_details,
        "golden_client_id",
        ["address_line1", "email"],
        noise_rates["stale_crm_address"],
        rngs
    )

    # Replace some legal first names with common nicknames.
    contacts_df = apply_nicknames(
        contacts_df,
        "first_name",
        noise_rates["nicknames_typos"],
        rngs
    )

    # Introduce spelling errors in some first names to simulate
    # inconsistent data entry in the CRM.
    contacts_df = introduce_typos(
        contacts_df,
        "first_name",
        noise_rates["nicknames_typos"],
        rngs
    )

    # Remove either email or phone information from selected records
    # to simulate incomplete CRM contact information.
    contacts_df = introduce_missing_values(
        contacts_df,
        ["email", "phone"],
        noise_rates["missing_contact_info"],
        rngs
    )

    # Create additional CRM records for existing clients.
    # These records receive new contact IDs but retain the same golden
    # client ID so the duplicates can be identified using ground truth.
    contacts_df = introduce_duplicates(
        contacts_df,
        noise_rates["crm_duplicates"],
        rngs,
        "contact_id",
        "CRM_DUP"
    )

    # Generate additional CRM prospects who do not have an existing
    # golden client record or an associated investment account
    orphan_count = round(
        len(golden_clients) * noise_rates["crm_orphans"]
    )

    orphan_contacts = []

    for number in range(orphan_count):

        created_at = fake.date_time_between(
            start_date="-5y",
            end_date="now"
        )

        # Orphan prospects have their own CRM IDs but no golden client ID.
        orphan_contact = {
            "contact_id": f"CRM_ORPHAN{number + 1:06d}",
            "golden_client_id": None,
            "first_name": fake.first_name(),
            "middle_name": fake.first_name(),
            "last_name": fake.last_name(),
            "dob": None,
            "email": fake.email(),
            "phone": fake.phone_number(),
            "address_line1": fake.street_address(),
            "city": fake.city(),
            "state": fake.state_abbr(),
            "zip": fake.zipcode(),
            "segment": None,
            "advisor_id": None,
            "created_at": created_at,
            "updated_at": created_at
        }

        orphan_contacts.append(orphan_contact)

    orphan_contacts_df = pd.DataFrame(orphan_contacts)

    # Combine original contacts, duplicate records, and orphan prospects.
    contacts_df = pd.concat(
        [contacts_df, orphan_contacts_df],
        ignore_index=True
    )

    return contacts_df

def generate_crm_interactions(contacts, rngs):
    fake = rngs["faker"]
    rng = rngs["python"]

    if contacts.empty:
        raise ValueError("Cannot generate interactions without CRM contacts.")

    # defining the interaction types and channels supported by the CRM source.
    interaction_types = [
        "MEETING",
        "CALL",
        "EMAIL",
        "REVIEW",
        "COMPLAINT"
    ]

    channels = [
        "IN_PERSON",
        "PHONE",
        "VIDEO",
        "PORTAL"
    ]

    sentiments = [
        "POSITIVE",
        "NEUTRAL",
        "NEGATIVE"
    ]

    case_statuses = [
        "OPEN",
        "CLOSED"
    ]

    interactions = []

    # Generate interaction records for each CRM contact, including
    # duplicate contacts and orphan prospects.
    interaction_number = 1

    for _, contact in contacts.iterrows():
        # for each contact get contact_id
        contact_id = contact["contact_id"]

        # then randomly generate between 1 and 10 interactions for each contact
        number_of_interactions = rng.randint(1, 10)

        for _ in range(number_of_interactions):

            # for that contact, randomly determine the type of interaction.
            interaction_type = rng.choice(interaction_types)

            # Generate an interaction date on or after the contact's
            # creation date and no later than today
            interaction_date = fake.date_between(
                start_date=contact["created_at"].date(),
                end_date="today"
            )

            # Only complaint interactions are treated as formal complaints.
            is_complaint = (interaction_type == "COMPLAINT")

            # Assign a case status to complaints; other interactions
            # do not have an applicable case status.
            if is_complaint:
                case_status = rng.choice(case_statuses)
            else:
                case_status = None

            # Create a unique interaction record linked to its CRM contact.
            interaction = {
                "interaction_id": f"INT{interaction_number:010d}",
                "contact_id": contact_id,
                "interaction_type": interaction_type,
                "channel": rng.choice(channels),
                "interaction_date": interaction_date,
                "sentiment": rng.choice(sentiments),
                "is_complaint": is_complaint,
                "case_status": case_status,
                "notes": fake.sentence(nb_words=10)
            }

            interactions.append(interaction)

            # increment the counter to ensure every interaction has a unique ID and move to next interaction
            interaction_number += 1

    # Convert all generated interaction records into a DataFrame.
    interactions_df = pd.DataFrame(interactions)

    return interactions_df