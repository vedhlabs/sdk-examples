from lending.app import app


def connect():
    """Approval-only access to the connection owned by the Lending App."""
    return app.client
