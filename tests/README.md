# Tests

This directory contains comprehensive tests for the News Aggregator application using pytest.

## Test Structure

- `conftest.py` - Pytest configuration and shared fixtures
- `test_config.py` - Tests for configuration management
- `test_repository.py` - Tests for data repository layer
- `test_content_scraper.py` - Tests for content scraping functionality
- `test_feed_manager.py` - Tests for feed management
- `test_ai_summarizer.py` - Tests for AI summarization
- `test_integration.py` - Integration tests for the complete workflow

## Running Tests

### Install Test Dependencies

```bash
pip install -r tests/requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Run only config tests
pytest tests/test_config.py

# Run only repository tests
pytest tests/test_repository.py

# Run only integration tests
pytest tests/test_integration.py
```

### Run Tests with Coverage

```bash
pytest --cov=src --cov-report=html
```

This will generate an HTML coverage report in `htmlcov/index.html`.

### Run Tests by Category

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

### Verbose Output

```bash
pytest -v
```

## Test Features

### Fixtures

- `test_db_url` - Creates temporary database for testing
- `test_config` - Provides test configuration
- `test_repository` - Creates fresh repository for each test
- `sample_feed_data` - Sample feed data for testing
- `sample_article_data` - Sample article data for testing

### Mocking

Tests use `unittest.mock` and `pytest-mock` to mock external dependencies:

- HTTP requests for content scraping
- OpenAI API calls for summarization
- RSS feed parsing

### Test Database

Each test uses a temporary SQLite database that is automatically cleaned up after the test completes.

## Adding New Tests

When adding new functionality:

1. Create tests in the appropriate `test_*.py` file
2. Use the existing fixtures for common setup
3. Mock external dependencies
4. Include both success and failure cases
5. Test error handling

Example test structure:

```python
def test_new_functionality(self, test_repository, sample_data):
    """Test description"""
    # Arrange
    setup_test_data()

    # Act
    result = function_under_test()

    # Assert
    assert result.is_expected()
```
