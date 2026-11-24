import random
from pathlib import Path

import numpy as np
import yaml
from faker import Faker


def load_config(config_path: str) -> dict:
    config_path = Path(config_path)

    # reading the yaml files and covering edge cases like
    # whether or not it exists
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # checks if the yaml is in the right format
    if not isinstance(config, dict):
        raise ValueError("Configuration must contain a YAML dictionary.")

    # checks for synthetic data
    if "synthetic_data" not in config:
        raise ValueError("Missing 'synthetic_data' configuration section.")

    # stores the synthetic_data info and required attributes (seed, scale, noise_rates)
    # that are needed to generate data into variables 
    synthetic_config = config["synthetic_data"]

    required_sections = ["seed", "scale", "noise_rates"]

    # check if the required_sections are in syntehtic_data inside the dev.yml file
    for section in required_sections:
        if section not in synthetic_config:
            raise ValueError(
                f"Missing '{section}' in synthetic_data configuration."
            )


    scale = synthetic_config["scale"]
    noise_rates = synthetic_config["noise_rates"]

    required_scale = [
        "clients",
        "households",
        "advisors",
        "branches",
        "securities"
    ]

    # check if required_scale attributes are present inside scale in dev.yml
    for key in required_scale:
        if key not in scale:
            raise ValueError(f"Missing scale parameter: {key}")

        if not isinstance(scale[key], int) or isinstance(scale[key], bool) or scale[key] <= 0:
            raise ValueError(f"Scale parameter '{key}' must be a positive integer.")

    # households cant be greater than clients
    if scale["households"] > scale["clients"]:
        raise ValueError("Household count cannot exceed client count.")

    # check if the rates are numeric and betweek 0 and 1
    for key, rate in noise_rates.items():
        if not isinstance(rate, (int, float)) or isinstance(rate, bool):
            raise ValueError(f"Noise rate '{key}' must be numeric.")

        if not 0 <= rate <= 1:
            raise ValueError(f"Noise rate '{key}' must be between 0 and 1.")

    if not isinstance(synthetic_config["seed"], int) or isinstance(synthetic_config["seed"], bool):
        raise ValueError("Random seed must be an integer.")

    return config


def initialize_random_generators(seed: int) -> dict:
    python_rng = random.Random(seed)

    numpy_rng = np.random.default_rng(seed)

    fake = Faker("en_US")
    fake.seed_instance(seed)

    return {
        "python": python_rng,
        "numpy": numpy_rng,
        "faker": fake
    }
