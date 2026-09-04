from example_support.config import connect as connect_client


def connect():
    """Create low-level transport access for the webhook operator boundary."""
    return connect_client("ecommerce-dev")
