import hashlib
import pandas as pd

def generate_households(config, rngs):
    rng = rngs["python"]

    # get client_count and household_count from dev.yml
    client_count = config["synthetic_data"]["scale"]["clients"]
    household_count = config["synthetic_data"]["scale"]["households"]

    # creating  unique client_ids for clients and households
    client_ids = []

    # this is for creating client_ids to assign to households, not creating actual clients
    for number in range(client_count):
        # creates a random client id
        golden_client_id = f"GC{number + 1:06d}"
        client_ids.append(golden_client_id)
    
    household_ids = []

    for number in range(household_count):
        household_id = f"HH{number + 1:06d}"
        household_ids.append(household_id)

    # shuffling client_ids so they are distributed randomly
    rng.shuffle(client_ids)

    household_members = []

    # give every household one single client first
    for number, household_id in enumerate(household_ids):
        household_members.append({
            "household_id": household_id,
            "golden_client_id": client_ids[number],
            "relationship": "HEAD"
        })

    # then distribute the remaining clients across existing households
    # takes all client ids starting from the position immediately after the first houseold_count clients
    remaining_client_ids = client_ids[household_count:]

    for golden_client_id in remaining_client_ids:
        # choose a random household
        household_id = rng.choice(household_ids)

        # choose relationship to the only client in the household right now as either spouse or dependent
        relationship = rng.choice([
            "SPOUSE",
            "DEPENDENT"
        ])

        household_members.append({
            "household_id": household_id,
            "golden_client_id": golden_client_id,
            "relationship": relationship
        })
    
    households = pd.DataFrame(household_members)

    return households


def generate_clients(config, households, advisors, rngs):
    fake = rngs["faker"]
    rng = rngs["python"]
    np_rng = rngs["numpy"]

    client_count = config["synthetic_data"]["scale"]["clients"]

    # make sure households and advisors exist
    if households.empty:
        raise ValueError("Cannot generate clients without households.")

    if advisors.empty:
        raise ValueError("Cannot generate clients without advisors.")


    # generateing a lognormal AUM value for each client
    target_aum_values = np_rng.lognormal(
        mean=11,
        sigma=1.2,
        size=client_count
    )

    # then sort clients by AUM to assign wealth segments
    # argsort sorts and returns a list of the indices that would sort the original array
    # and [::-1] reverses it so it will then be a list of indices that makes the original array in desc order
    sorted_indices = target_aum_values.argsort()[::-1]

    # this will calculate the number of clients in each segment
    # uhnw = ultra high net worth, hnw = high net worth
    uhnw_count = round(client_count * 0.05)
    hnw_count = round(client_count * 0.25)
    # mass_affluent_count = client_count - uhnw_count - hnw_count

    # assign wealth segments into uhnw, hnw, and mass affluent based on AUM ranking
    segments = [None] * client_count

    for index in sorted_indices[:uhnw_count]:
        segments[index] = "UHNW"

    for index in sorted_indices[uhnw_count:uhnw_count + hnw_count]:
        segments[index] = "HNW"

    for index in sorted_indices[uhnw_count + hnw_count:]:
        segments[index] = "MASS_AFFLUENT"

    # then we map each client ID to its assigned household
    household_lookup = {}

    # iterating over every row as a Series
    # make sure the client is assigned to that household
    for _, row in households.iterrows():
        household_lookup[row["golden_client_id"]] = row["household_id"]

    # get all the advisor IDs available for assignment
    advisor_ids = list(advisors["advisor_id"])

    clients = []

    # this creates the actual clients
    for number in range(client_count):
        golden_client_id = f"GC{number + 1:06d}"

        first_name = fake.first_name()
        middle_name = fake.first_name()
        last_name = fake.last_name()

        # Generate a synthetic tax ID and store only its SHA-256 hash.
        synthetic_tax_id = fake.ssn()

        tax_id_hash = hashlib.sha256(
            synthetic_tax_id.encode("utf-8")
        ).hexdigest()

        # generating client location and contact info
        dob = fake.date_between(
            start_date="-90y",
            end_date="-18y"
        )

        email = fake.email()
        phone = fake.phone_number()

        address_line1 = fake.street_address()
        city = fake.city()
        state = fake.state_abbr()
        zip_code = fake.zipcode()

        # gnerate client kyc status, riskProfile, and onboarding date
        kyc_status = rng.choice([
            "VERIFIED",
            "PENDING",
            "EXPIRED"
        ])

        risk_profile = rng.choice([
            "CONSERVATIVE",
            "MODERATE",
            "GROWTH",
            "AGGRESSIVE"
        ])

        onboarding_date = fake.date_between(
            start_date="-20y",
            end_date="today"
        )

        # picking a random advisor for a client
        advisor_id = rng.choice(advisor_ids)

        client = {
            "golden_client_id": golden_client_id,
            "household_id": household_lookup[golden_client_id],
            "first_name": first_name,
            "middle_name": middle_name,
            "last_name": last_name,
            "dob": dob,
            "tax_id_hash": tax_id_hash,
            "email": email,
            "phone": phone,
            "address_line1": address_line1,
            "city": city,
            "state": state,
            "zip": zip_code,
            "segment": segments[number],
            "advisor_id": advisor_id,
            "kyc_status": kyc_status,
            "risk_profile": risk_profile,
            "onboarding_date": onboarding_date,
            "target_aum": round(target_aum_values[number], 2)
        }

        clients.append(client)

    golden_clients = pd.DataFrame(clients)

    return golden_clients
