from ecommerce.app import app


def connect():
    """Webhook-only access to the connection owned by the Ecommerce App."""
    return app.client
