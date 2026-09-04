from example_support.config import connect as connect_client


def connect():
    """Create low-level transport access for the approval operator boundary."""
    return connect_client("lending-dev")
