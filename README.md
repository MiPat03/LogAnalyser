# Log Analyzer

A web application for uploading, parsing, storing, filtering, and visualizing Apache server logs. Built with Flask, Dash, SQLite, and Plotly for interactive analytics.

---

## Features

- **Upload & Process Logs:** Upload Apache log files via a user-friendly web interface.
- **Efficient Parsing:** Asynchronous, duplicate-safe log parsing with progress tracking.
- **Advanced Filtering:** Filter logs by file, status code, IP address, request type, and more.
- **Persistent Storage:** Stores parsed logs in a robust SQLite database (WAL mode for concurrent access).
- **Interactive Visualizations:** Explore dashboards and analytics with Plotly and Dash (status codes, request types, top IPs/APIs, user agents, response times, and more).
- **Export Options:** Download filtered log data as CSV or JSON.
- **API Access:** Query logs via a REST API endpoint.
- **File Management:** Delete uploaded files and reset all data from the dashboard.
- **Docker Support:** Easily containerize and deploy the application.

---

## Apache Log Format

This application expects Apache server logs in the following format:

