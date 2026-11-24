import pandas as pd

def _get_rng(rngs):
    return rngs["python"]

def _get_sample_indices(df, rate, rng):
    if not 0 <= rate <= 1:
        raise ValueError("Noise rate must be in between 0 and 1")
    
    # size of the noisy data
    sample_size = round(len(df) * rate)

    # returns a subset of df (number of rows = sample_size) and that will be 
    # used to create noise in the data
    return rng.sample(list(df.index), sample_size)

# introducting typos in the synthetic data
def introduct_typos(df, column, rate, rngs):
    df = df.copy()
    rng = _get_rng(rngs)

    # get the indexes to add noise to
    indices = _get_sample_indices(df, rate, rng)

    for index in indices:
        # get value from a particular index and column
        # check if its a string or if its a single character and if it is, continue
        value = df.at[index, column]
        if not isinstance(value, str) or len(value) < 2:
            continue

        # find a random position to replace and
        # find a random character to replace it with 
        position = rng.randint(0, len(value) - 1)
        replacement = rng.choice("abcdefghijklmnopqrstuvwxyz")

        # add the typo to that record with index = index
        df.at[index, column] = (
            value[:position] + replacement + value[position:]
        )
    
    return df

def apply_nicknames(df, column, rate, rngs):
    df = df.copy()
    rng = _get_rng(rngs)

    nickname_map = {
        "Robert": ["Bob", "Rob", "Bobby"],
        "William": ["Will", "Bill", "Billy"],
        "James": ["Jim", "Jimmy"],
        "Richard": ["Rick", "Rich"],
        "Michael": ["Mike", "Mikey"],
        "Elizabeth": ["Liz", "Beth", "Lizzie"],
        "Jennifer": ["Jen", "Jenny"],
        "Katherine": ["Kate", "Kathy", "Katie"],
        "Margaret": ["Maggie", "Meg", "Peggy"],
        "Patricia": ["Pat", "Patty", "Trish"],
        "Thomas": ["Tom", "Tommy"],
        "Charles": ["Charlie", "Chuck"],
        "Joseph": ["Joe", "Joey"],
        "Daniel": ["Dan", "Danny"],
        "Anthony": ["Tony"],
        "Christopher": ["Chris"],
        "Matthew": ["Matt"],
        "Benjamin": ["Ben", "Benny"],
        "Nicholas": ["Nick", "Nicky"],
        "Alexander": ["Alex"],
        "Samuel": ["Sam", "Sammy"],
        "Andrew": ["Andy", "Drew"],
        "Jonathan": ["Jon", "Johnny"],
        "Rebecca": ["Becky"],
        "Susan": ["Sue", "Susie"],
        "Deborah": ["Deb", "Debbie"],
        "Dorothy": ["Dot", "Dottie"],
        "Catherine": ["Cathy", "Cat"],
        "Stephanie": ["Steph"],
        "Christina": ["Chris", "Tina"]
    }

    eligible_indices = []

    for index in df.index:
        # select a particular record
        value = df.at[index, column]
        if not isinstance(value, str):
            continue

        if value not in nickname_map:
            continue

        # getting all indexes to change name to nickname
        eligible_indices.append(index)

    sample_size = round(len(df)*rate)

    # sample size from rate cant be greater than teh number of eligible indices
    if sample_size > len(eligible_indices):
        sample_size = len(eligible_indices)
    
    # from eligible_indices list, it picks out sample_size number of indices
    indices = rng.sample(eligible_indices, sample_size)
    
    for index in indices:
        value = df.at[index, column]

        # picks a random nickname for that name
        nickname = rng.choice(nickname_map[value])

        # assigns that nickname to the df
        df.at[index, column] = nickname

    return df

def introduce_missing_values(df, columns, rate, rngs):
    df = df.copy()
    rng = _get_rng(rngs)

    if not columns:
        return df
    
    indices = _get_sample_indices(df, rate, rng)

    for index in indices:
        # choose a random column
        column = rng.choice(columns)
        # make that value at (index, column) = None
        df.at[index, column] = None

    return df

def vary_phone_formats(df, column, rate, rngs):
    df = df.copy()
    rng = _get_rng(rngs)

    indices = _get_sample_indices(df, rate, rng)

    for index in indices:
        value = df.at[index, column]

        if not isinstance(value, str):
            continue

        digits = ""

        # only add to digits if its a string
        for char in value:
            if char.isdigit():
                digits += char

        if len(digits) != 10:
            continue

        formats = [
            f"{digits[:3]}-{digits[3:6]}-{digits[6:]}",
            f"({digits[:3]}) {digits[3:6]}-{digits[6:]}",
            f"{digits[:3]}.{digits[3:6]}.{digits[6:]}",
            f"{digits[:3]} {digits[3:6]} {digits[6:]}"
        ]

        # randomize the phone number format
        df.at[index, column] = rng.choice(formats)

    return df


def vary_address_format(df, column, rate, rngs):
    df = df.copy()
    rng = _get_rng(rngs)

    replacements = {
        "Street": "St",
        "Road": "Rd",
        "Avenue": "Ave",
        "Boulevard": "Blvd",
        "Drive": "Dr",
        "Lane": "Ln",
        "Court": "Ct",
        "Apartment": "Apt"
    }

    indices = _get_sample_indices(df, rate, rng)

    for index in indices:
        value = df.at[index, column]

        if not isinstance(value, str):
            continue

        for original, abberiviated in replacements.items():
            if original in value:
                value.replace(original, abberiviated)
        
        df.at[index, column] = value

    return df


# if there were any changes in contact details, they are compared using
# reference_df and 
def introduce_stale_contact_details(
    df,
    reference_df,
    key_column,
    columns,
    rate,
    rngs
):
    df = df.copy()
    rng = _get_rng(rngs)

    reference = reference_df.set_index(key_column)

    indices = _get_sample_indices(df, rate, rng)

    for index in indices:
        key = df.at[index, key_column]

        if key not in reference.index:
            continue

        column = rng.choice(columns)

        old_value = reference.at[key, column]
        current_value = df.at[index, column]

        if isinstance(old_value, pd.Series):
            continue

        if pd.notna(old_value) and old_value != current_value:
            df.at[index, column] = old_value

    return df


def introduce_duplicates(
    df,
    rate,
    rngs,
    id_column,
    duplicate_id_prefix="DUP"
):
    df = df.copy()
    rng = _get_rng(rngs)

    indices = _get_sample_indices(df, rate, rng)

    duplicates = df.loc[indices].copy()

    existing_ids = set(df[id_column].dropna())

    new_ids = []

    # loops through every duplicated record and generates a new ID
    for number in range(len(duplicates)):
        new_id = f"{duplicate_id_prefix}-{number + 1:06d}"

        # if the generated id already exists, it icrements the number
        while new_id in existing_ids:
            number += 1
            new_id = f"{duplicate_id_prefix}-{number + 1:06d}"

        # save the new ID
        new_ids.append(new_id)
        existing_ids.add(new_id)

    duplicates[id_column] = new_ids

    return pd.concat([df, duplicates], ignore_index=True)


def introduce_dq_anomalies(
    df,
    numeric_columns,
    date_columns,
    rate,
    rngs,
    as_of_date
):
    df = df.copy()
    rng = _get_rng(rngs)

    available_columns = numeric_columns + date_columns

    if not available_columns:
        return df

    indices = _get_sample_indices(df, rate, rng)

    for index in indices:
        # randomly selects a column for each row
        column = rng.choice(available_columns)
        
        # if that column is a numeric column introduce numeric anomalies to it
        if column in numeric_columns:
            value = df.at[index, column]

            # if the value at (index, column) is not None:
            # 1. if its non zero -> make it negative of its absolute value
            # 2. else if its 0, then make it -1
            if pd.notna(value):
                if value != 0:
                    df.at[index, column] = -abs(value)
                else:
                    df.at[index, column] = -1

        # introduce date anomalies to the data
        elif column in date_columns:
            value = pd.to_datetime(
                df.at[index, column],
                errors="coerce"   # errors="coerce" means invalid dates are converted to NaT rather than causing an exception
            )
            
            # if the data is not None, change the date by adding a random number of days between 1 and 365
            if pd.notna(value):
                future_days = rng.randint(1, 365)

                df.at[index, column] = (
                    pd.Timestamp(as_of_date)
                    + pd.Timedelta(days=future_days)
                )

    return df
