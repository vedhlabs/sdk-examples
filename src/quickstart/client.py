from quickstart.app import app


def connect():
    """Operator-only access to the connection owned by the Quickstart App."""
    return app.client
