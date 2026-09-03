from trading.app import app


def connect():
    """Operator-only access to the connection owned by the Trading App."""
    return app.client
