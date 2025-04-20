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

``` IP Remote-LogName User-ID [Timestamp] "Request-Type API Protocol" Status-Code Bytes "Referrer" "User-Agent" Response-Time ```


---

## Installation

1. **Clone the repository:**
    ```
    git clone https://github.com/yourusername/log-analyzer.git
    cd log-analyzer
    ```
2. **Install dependencies:**
    ```
    pip install -r requirements.txt
    ```
3. **Initialize the database:**
    ```
    python -c "from app import init_db; init_db()"
    ```
4. **Run the application:**
    ```
    python app.py
    ```
5. **Open your browser and navigate to:**  
   ```
   [http://localhost:5000](http://localhost:5000)
    ```

---

## Docker Usage

Build and run the application using Docker:

<pre> docker build -t log-analyzer .
    
docker run -p 5000:5000 log-analyzer </pre>

## License

MIT License

