import os
# Configure test environment to avoid external network timeouts during unit testing
os.environ["ENVIRONMENT"] = "test"
os.environ["SUPABASE_URL"] = ""
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

import pytest
from src.db.supabase_client import reset_mock_db


@pytest.fixture(autouse=True)
def clean_database():
    """Ensures mock database is fresh before each test run."""
    reset_mock_db()
    yield
    reset_mock_db()
