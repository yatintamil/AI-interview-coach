"""
Domain Exceptions for AI Interview Coach platform.
"""

class ResumeParsingError(Exception):
    """Raised when document parsing fails."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class ExtractionError(Exception):
    """Raised when entity extraction fails."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class NotFoundError(Exception):
    """Raised when requested resource does not exist."""
    def __init__(self, entity_name: str, entity_id: str):
        self.message = f"{entity_name} with id {entity_id} not found."
        super().__init__(self.message)
