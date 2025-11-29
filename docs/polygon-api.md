# Polygon API Integration

The Polygon API integration provides functionality to fetch stock market data from Polygon.io, including AAPL stock prices for the last 7 days (or any custom period).

## Setup

To use the Polygon API integration, you need to:

1. Set the `POLYGON_API_KEY` environment variable with your Polygon API key:

```bash
export POLYGON_API_KEY="your_api_key_here"
```

## Usage

### Fetch AAPL Prices (Last 7 Days)

```python
from edgar import fetch_aapl_last_7_days

# Fetch AAPL prices for the last 7 days
state = fetch_aapl_last_7_days()

print(state['prices'])  # List of price data
print(state['timestamp'])  # When the data was fetched
```

### Fetch Any Stock Prices

```python
from edgar import fetch_aapl_prices

# Fetch MSFT prices for the last 30 days
state = fetch_aapl_prices(ticker='MSFT', days=30)
```

### Get Current Prices State

```python
from edgar import get_prices_state

# Load the current prices state from file
state = get_prices_state()

# Access the data
for price_data in state['prices']:
    print(f"{price_data['date']}: Close=${price_data['close']}, Volume={price_data['volume']}")
```

## State File

The fetched prices are automatically saved to `data/prices_state.json` with the following structure:

```json
{
  "timestamp": "2024-01-01T12:00:00.000000",
  "prices": [
    {
      "date": "2024-01-01",
      "close": 150.25,
      "volume": 52000000
    },
    {
      "date": "2024-01-02",
      "close": 151.50,
      "volume": 48000000
    }
  ],
  "last_fetch_timestamp": "2024-01-02T12:00:00.000000"
}
```

## Error Handling

All API errors are logged to `~/fetch_errors.log` with timestamps. If the API is unavailable or the API key is missing, a `PolygonAPIError` exception is raised.

```python
from edgar import fetch_aapl_prices, PolygonAPIError

try:
    state = fetch_aapl_prices()
except PolygonAPIError as e:
    print(f"Error: {e}")
```

## API Functions

### fetch_aapl_last_7_days(api_key=None)

Convenience function to fetch AAPL stock prices for the last 7 days.

**Parameters:**
- `api_key` (str, optional): Polygon API key. If not provided, uses POLYGON_API_KEY environment variable.

**Returns:**
- dict: State dictionary with timestamp, prices list, and last_fetch_timestamp

**Raises:**
- `PolygonAPIError`: If API call fails

### fetch_aapl_prices(ticker='AAPL', days=7, api_key=None)

Fetch stock prices for the specified ticker and date range.

**Parameters:**
- `ticker` (str): Stock ticker symbol (default: 'AAPL')
- `days` (int): Number of days to fetch (default: 7)
- `api_key` (str, optional): Polygon API key. If not provided, uses POLYGON_API_KEY environment variable.

**Returns:**
- dict: State dictionary with timestamp, prices list, and last_fetch_timestamp

**Raises:**
- `PolygonAPIError`: If API call fails

### get_prices_state()

Load the prices state from the state file.

**Returns:**
- dict: State dictionary with timestamp, prices list, and last_fetch_timestamp

### save_prices_state(state)

Save the prices state to the state file.

**Parameters:**
- `state` (dict): Dictionary containing timestamp, prices, and last_fetch_timestamp

**Raises:**
- `PolygonAPIError`: If file write fails

## Testing

Run the test suite for the Polygon API integration:

```bash
pytest tests/test_polygon.py -v
```
