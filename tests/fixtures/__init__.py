"""CompIntel test fixtures package (Rule R-MD-11)."""

from tests.fixtures.synthetic import (
    SyntheticDataGenerator,
    generate_synthetic_observations_df,
    generate_synthetic_raw_records_df,
)

__all__ = [
    "SyntheticDataGenerator",
    "generate_synthetic_observations_df",
    "generate_synthetic_raw_records_df",
]
