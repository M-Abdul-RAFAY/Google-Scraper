# Tools Directory

This folder contains various utility and diagnostic tools for the Google Business Scraper.

## Files Description

### `advanced_scraper.py`

Extended version of the scraper with additional features and configurations. Contains advanced scraping methods and enhanced data extraction capabilities.

### `analyze_structure.py`

Diagnostic tool to analyze the HTML structure of Google Maps pages. Useful for debugging and understanding the current page layout when selectors stop working.

### `config.py`

Configuration file containing settings, constants, and configuration parameters for the scraper.

### `diagnose.py`

Diagnostic tool to test ChromeDriver setup and basic browser functionality. Use this when troubleshooting setup issues.

### `test_data_extraction.py`

Tool to test and validate data extraction methods. Useful for testing specific extraction functions without running the full scraper.

### `test_scraper.py`

Comprehensive testing suite for the scraper functionality. Contains unit tests and integration tests.

### `utils.py`

Utility functions and helper methods used by the main scraper. Contains data processing, validation, and formatting functions.

## Usage

These tools are intended for development, debugging, and testing purposes. You can run them individually to:

- Test specific functionality
- Diagnose issues
- Analyze Google Maps page structure
- Validate data extraction methods

Example:

```bash
python tools/diagnose.py
python tools/analyze_structure.py
```
