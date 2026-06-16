import pytest
from unittest.mock import patch
from src.app import app


class MockEvent:
    def __init__(self, **kwargs):
        self.data = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

    def model_dump(self, by_alias=True):
        return self.data


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_forexfactory_daily_success(client):
    """
    Test that the ForexFactory daily API route returns 200 OK and properly
    formats the mock data provided by forex-pytory.
    """
    # Create a mock EconomicEvent using the dummy class
    mock_event = MockEvent(
        Date="01/01/2020",
        Time="08:30",
        Currency="USD",
        Impact="High",
        Event="Non-Farm Employment Change",
        Actual="250K",
        Forecast="200K",
        Previous="150K",
    )

    with patch(
        "forex_pytory.core.scraper.forex_factory_scraper.get_url"
    ) as mock_get_url, patch(
        "forex_pytory.core.scraper.forex_factory_scraper.get_records"
    ) as mock_get_records:
        # Mock the return values
        mock_get_url.return_value = "http://mock-url.com"
        mock_get_records.return_value = [mock_event]

        # Make request to the Flask API
        response = client.get("/api/forex/daily?day=1&month=1&year=2020")

        # Assertions
        assert response.status_code == 200
        data = response.get_json()

        assert "results" in data
        assert len(data["results"]) == 1

        result_event = data["results"][0]
        assert result_event["Event"] == "Non-Farm Employment Change"
        assert result_event["Currency"] == "USD"
        assert result_event["Impact"] == "High"


def test_missing_parameters(client):
    """
    Test that missing date parameters return a 400 Bad Request.
    """
    response = client.get("/api/forex/daily")
    assert response.status_code == 400
    assert "error" in response.get_json()
