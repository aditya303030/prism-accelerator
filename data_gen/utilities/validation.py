import pandas as pd

# make sure all required columns exist in 
def validate_required_columns(df, required_columns, dataframe_name):
    # Check that all expected columns exist in the DataFrame
    # and if missing, store it in missing_columns
    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"{dataframe_name} is missing required columns: {missing_columns}"
        )


# Check that required columns do not contain missing values.
def validate_not_null(df, columns, dataframe_name):
    for column in columns:
        if df[column].isna().any():
            missing_count = df[column].isna().sum()

            raise ValueError(
                f"{dataframe_name}.{column} contains {missing_count} null values."
            )


# Make sure the specified column contains unique identifiers.
def validate_unique(df, column, dataframe_name):
    duplicate_count = df[column].duplicated().sum()

    if duplicate_count > 0:
        raise ValueError(
            f"{dataframe_name}.{column} contains {duplicate_count} duplicate values."
        )


def validate_foreign_key(df,column,reference_df,reference_column,dataframe_name):
    # Collect the valid IDs from the referenced DataFrame.
    valid_ids = set(reference_df[reference_column].dropna())

    # Find non-null foreign-key values that do not exist in the reference DataFrame.
    invalid_ids = (
        df.loc[
            # if the column is not null & its not in valid_ids
            df[column].notna() & ~df[column].isin(valid_ids),
            column
        ]
        .unique()
    )

    if len(invalid_ids) > 0:
        raise ValueError(
            f"{dataframe_name}.{column} contains invalid references: "
            f"{list(invalid_ids[:5])}"
        )


def validate_non_negative(df, columns, dataframe_name):
    # Check that specified numeric columns do not contain negative values.
    for column in columns:
        # count how many columns are negative
        negative_count = (df[column] < 0).sum()

        # if its negative raise an error
        if negative_count > 0:
            raise ValueError(
                f"{dataframe_name}.{column} contains "
                f"{negative_count} negative values."
            )
        
        