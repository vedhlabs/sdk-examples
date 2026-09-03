from primitives.app import app


def connect():
    """Signal-only access to the connection owned by the Primitives App."""
    return app.client
