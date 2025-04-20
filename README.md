# Log Analyzer

A web application for analyzing Apache server logs with filtering, visualization, and storage capabilities.

## Features

- **Upload and Process**: Upload Apache log files through a user-friendly interface
- **Parse and Filter**: Process logs by various filters (log level, timestamp, IP, etc.)
- **Persistent Storage**: Store parsed log data in a SQLite database for future access
- **Visualizations**: View metrics and graphs based on your log data
- **Export Options**: Export your log data as JSON or CSV

## Apache Log Format

This application is designed to work with Apache server logs in the following format:

```
IP Remote-LogName User-ID [Timestamp] "Request-Type API Protocol" Status-Code Bytes "Referrer" "User-Agent" Response-Time
```

Example:
```
192.168.1.1 - john [10/Oct/2023:13:55:36 +0000] "GET /api/users HTTP/1.1" 200 2326 "http://example.com" "Mozilla/5.0" 0.003
```

## Installation

1. Clone this repository
2. Install the required dependencies:

```
pip install -r requirements.txt
```

3. Run the application:

```
python app.py
```

4. Open your browser and navigate to `http://localhost:5000`

## Usage

1. **Upload Log Files**: From the home page, upload your Apache log files
2. **View Dashboard**: See an overview of your log data on the dashboard
3. **Browse Logs**: View and filter log entries on the logs page
4. **Analyze Data**: Explore visualizations and metrics on the analytics page

## Project Structure

- `app.py`: Main Flask application
- `templates/`: HTML templates for the web interface
- `static/`: CSS, JavaScript, and other static files
- `uploads/`: Directory for uploaded log files
- `log_data.db`: SQLite database for storing parsed log data

## Requirements

- Python 3.7+
- Flask
- SQLite
- Pandas
- Plotly
- Other dependencies listed in requirements.txt

## License

MIT License
