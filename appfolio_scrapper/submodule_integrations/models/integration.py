class Integration:
    """Minimal base class shared by integration implementations."""

    def __init__(self, integration_name: str):
        self.integration_name = integration_name
