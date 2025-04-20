from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename
import os
import json
import re
from datetime import datetime
import sqlite3
import plotly
import plotly.graph_objects as go

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'loganalyzer_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATABASE'] = 'log_data.db'
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024  # 300MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Regular expression for parsing Apache logs
APACHE_LOG_PATTERN = r'(\S+) (\S+) (\S+) \[([\w:/]+\s[+\-]\d{4})\] "(\S+) (\S+) (\S+)" (\d+) (\S+) "([^"]*)" "([^"]*)" (\S+)'

def get_db_connection():
    """Get a new database connection with timeout and proper settings"""
    conn = sqlite3.connect(app.config['DATABASE'], timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def init_db():
    """Initialize the database with the required tables"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Create logs table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            ip TEXT,
            remote_log_name TEXT,
            user_id TEXT,
            timestamp TEXT,
            request_type TEXT,
            api TEXT,
            protocol TEXT,
            status_code INTEGER,
            bytes INTEGER,
            referrer TEXT,
            user_agent TEXT,
            response_time REAL,
            upload_date TEXT
        )
        ''')
        
        # Create files table to track uploaded files
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT UNIQUE,  
            upload_date TEXT,
            record_count INTEGER
        )
        ''')
        
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def parse_apache_log(log_line):
    """Parse a single Apache log line into its components"""
    match = re.match(APACHE_LOG_PATTERN, log_line)
    if match:
        return {
            'ip': match.group(1),
            'remote_log_name': match.group(2),
            'user_id': match.group(3),
            'timestamp': match.group(4),
            'request_type': match.group(5),
            'api': match.group(6),
            'protocol': match.group(7),
            'status_code': int(match.group(8)),
            'bytes': match.group(9),
            'referrer': match.group(10),
            'user_agent': match.group(11),
            'response_time': float(match.group(12))
        }
    return None

def process_log_file_async(file_path, file_name):
    """Process the log file asynchronously and store data in the database"""
    global processing_status
    
    try:
        # Count total lines for progress tracking
        total_lines = 0
        with open(file_path, 'r') as f:
            for _ in f:
                total_lines += 1
        
        processing_status[file_name]['total'] = total_lines
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        record_count = 0
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Create a set to track unique log entries
        processed_logs = set()
        processed_line_count = 0
        
        # Process in smaller batches for better performance
        batch_size = 500
        current_batch = []
        
        with open(file_path, 'r') as f:
            for line in f:
                processed_line_count += 1
                
                # Update progress every 100 lines
                if processed_line_count % 100 == 0:
                    progress_percent = int((processed_line_count / total_lines) * 100)
                    processing_status[file_name]['progress'] = progress_percent
                
                log_data = parse_apache_log(line.strip())
                if log_data:
                    # Create a unique identifier for this log entry
                    log_key = (
                        log_data['ip'],
                        log_data['timestamp'],
                        log_data['request_type'],
                        log_data['api'],
                        log_data['status_code']
                    )
                    
                    # Skip if we've already processed this exact log entry
                    if log_key in processed_logs:
                        continue
                    
                    # Add to our set of processed logs
                    processed_logs.add(log_key)
                    
                    # Add to current batch
                    current_batch.append((
                        file_name, log_data['ip'], log_data['remote_log_name'], 
                        log_data['user_id'], log_data['timestamp'], log_data['request_type'], 
                        log_data['api'], log_data['protocol'], log_data['status_code'], 
                        log_data['bytes'], log_data['referrer'], log_data['user_agent'], 
                        log_data['response_time'], current_date
                    ))
                    
                    # Process batch if it reaches the batch size
                    if len(current_batch) >= batch_size:
                        cursor.executemany('''
                        INSERT INTO logs (
                            file_name, ip, remote_log_name, user_id, timestamp, 
                            request_type, api, protocol, status_code, bytes, 
                            referrer, user_agent, response_time, upload_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', current_batch)
                        
                        record_count += len(current_batch)
                        current_batch = []
                        conn.commit()
        
        # Process any remaining entries in the last batch
        if current_batch:
            cursor.executemany('''
            INSERT INTO logs (
                file_name, ip, remote_log_name, user_id, timestamp, 
                request_type, api, protocol, status_code, bytes, 
                referrer, user_agent, response_time, upload_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', current_batch)
            
            record_count += len(current_batch)
            conn.commit()
        
        # Update the file record with the correct record count
        cursor.execute('''
        UPDATE files SET record_count = ? WHERE file_name = ?
        ''', (record_count, file_name))
        
        conn.commit()
        
        # Update status to completed
        processing_status[file_name] = {
            'status': 'completed', 
            'progress': 100, 
            'total': total_lines,
            'processed': record_count
        }
        
        # Keep the completed status for at least 5 minutes to ensure the frontend can detect it
        print(f"Processing completed for {file_name}. Processed {record_count} records.")
        
    except Exception as e:
        print(f"Error processing file: {e}")
        processing_status[file_name] = {
            'status': 'error', 
            'error': str(e)
        }
    finally:
        if 'conn' in locals():
            conn.close()


def process_log_file(file_path, file_name):
    """Process the log file synchronously (legacy function)"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        record_count = 0
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Create a set to track unique log entries
        processed_logs = set()
        
        with open(file_path, 'r') as f:
            for line in f:
                log_data = parse_apache_log(line.strip())
                if log_data:
                    # Create a unique identifier for this log entry
                    log_key = (
                        log_data['ip'],
                        log_data['timestamp'],
                        log_data['request_type'],
                        log_data['api'],
                        log_data['status_code']
                    )
                    
                    # Skip if we've already processed this exact log entry
                    if log_key in processed_logs:
                        continue
                    
                    # Add to our set of processed logs
                    processed_logs.add(log_key)
                    
                    cursor.execute('''
                    INSERT INTO logs (
                        file_name, ip, remote_log_name, user_id, timestamp, 
                        request_type, api, protocol, status_code, bytes, 
                        referrer, user_agent, response_time, upload_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        file_name, log_data['ip'], log_data['remote_log_name'], 
                        log_data['user_id'], log_data['timestamp'], log_data['request_type'], 
                        log_data['api'], log_data['protocol'], log_data['status_code'], 
                        log_data['bytes'], log_data['referrer'], log_data['user_agent'], 
                        log_data['response_time'], current_date
                    ))
                    record_count += 1
                    
                    # Commit in batches to avoid long transactions
                    if record_count % 1000 == 0:
                        conn.commit()
        
        # Update the file record with the correct record count
        cursor.execute('''
        UPDATE files SET record_count = ? WHERE file_name = ?
        ''', (record_count, file_name))
        
        conn.commit()
        return record_count
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Database error: {e}")
        raise
    finally:
        conn.close()

@app.route('/')
def index():
    """Home page with file upload form"""
    return render_template('index.html')

import threading

# Global variable to track processing status
processing_status = {}

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle log file upload"""
    if 'logfile' not in request.files:
        flash('No file part', 'danger')
        return redirect(request.url)
    
    file = request.files['logfile']
    
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(request.url)
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Check if file with this name already exists and generate unique name if needed
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM files WHERE file_name = ?', (filename,))
            existing_file = cursor.fetchone()
            
            if existing_file:
                # Generate a unique filename by adding timestamp
                base_name, extension = os.path.splitext(filename)
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{base_name}_{timestamp}{extension}"
                # Rename the file
                new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.rename(file_path, new_file_path)
                file_path = new_file_path
            
            # Create initial file record with 0 records
            current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
            INSERT INTO files (file_name, upload_date, record_count)
            VALUES (?, ?, ?)
            ''', (filename, current_date, 0))
            conn.commit()
        except Exception as e:
            print(f"Error checking file: {e}")
        finally:
            conn.close()
        
        # Start processing in background thread
        processing_status[filename] = {'status': 'processing', 'progress': 0, 'total': 0}
        thread = threading.Thread(target=process_log_file_async, args=(file_path, filename))
        thread.daemon = True
        thread.start()
        
        # Redirect to index page with processing status
        return redirect(url_for('index', processing=filename))


@app.route('/processing_status/<file_name>')
def get_processing_status(file_name):
    """Get the processing status of a file"""
    if file_name in processing_status:
        status = processing_status[file_name]
        print(f"Status for {file_name}: {status['status']}")
        return jsonify(status)
    else:
        # Check if the file exists and has records
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT record_count FROM files WHERE file_name = ?', (file_name,))
            file_data = cursor.fetchone()
            
            if file_data and file_data['record_count'] > 0:
                # File exists and has been processed
                return jsonify({
                    'status': 'completed',
                    'progress': 100,
                    'processed': file_data['record_count']
                })
            else:
                return jsonify({'status': 'unknown'})
        except Exception as e:
            print(f"Error checking file status: {e}")
            return jsonify({'status': 'unknown'})
        finally:
            conn.close()

@app.route('/dashboard')
def dashboard():
    """Unified dashboard page with log statistics, logs, analytics, and history"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get total log count
        cursor.execute('SELECT COUNT(*) FROM logs')
        total_logs = cursor.fetchone()[0]
        
        # Get unique IP count
        cursor.execute('SELECT COUNT(DISTINCT ip) FROM logs')
        unique_ips = cursor.fetchone()[0]
        
        # Get error response count (status >= 400)
        cursor.execute('SELECT COUNT(*) FROM logs WHERE status_code >= 400')
        error_count = cursor.fetchone()[0]
        
        # Get all files first (including those with 0 records that are still processing)
        cursor.execute('''
        SELECT 
            file_name, 
            upload_date, 
            record_count
        FROM files
        ORDER BY upload_date DESC
        ''')
        files_basic = cursor.fetchall()
        
        # Get detailed stats for files that have logs
        cursor.execute('''
        SELECT 
            f.file_name, 
            COUNT(DISTINCT l.ip) as unique_ips,
            SUM(CASE WHEN l.status_code >= 400 THEN 1 ELSE 0 END) as error_count
        FROM files f 
        JOIN logs l ON f.file_name = l.file_name 
        GROUP BY f.file_name
        ''')
        file_stats = {row['file_name']: row for row in cursor.fetchall()}
        
        # Combine the data
        files = []
        for file in files_basic:
            # Convert sqlite3.Row to dict
            file_info = {key: file[key] for key in file.keys()}
            
            # Get stats if available
            if file['file_name'] in file_stats:
                stats = file_stats[file['file_name']]
                file_info['unique_ips'] = stats['unique_ips']
                file_info['error_count'] = stats['error_count']
            else:
                file_info['unique_ips'] = 0
                file_info['error_count'] = 0
                
            files.append(file_info)
        
        # Get data for analytics charts
        # Status code distribution
        cursor.execute('''
        SELECT status_code, COUNT(*) as count 
        FROM logs 
        GROUP BY status_code 
        ORDER BY count DESC
        ''')
        status_data = cursor.fetchall()
        
        # Request type distribution
        cursor.execute('''
        SELECT request_type, COUNT(*) as count 
        FROM logs 
        GROUP BY request_type 
        ORDER BY count DESC
        ''')
        request_data = cursor.fetchall()
        
        # Top 10 IPs
        cursor.execute('''
        SELECT ip, COUNT(*) as count 
        FROM logs 
        GROUP BY ip 
        ORDER BY count DESC 
        LIMIT 10
        ''')
        ip_data = cursor.fetchall()
        
        # Top 5 APIs
        cursor.execute('''
        SELECT api, COUNT(*) as count 
        FROM logs 
        GROUP BY api 
        ORDER BY count DESC 
        LIMIT 5
        ''')
        api_data = cursor.fetchall()
        
        # Create charts using Plotly
        status_labels = [str(row['status_code']) for row in status_data]
        status_values = [row['count'] for row in status_data]
        status_fig = go.Figure(data=[go.Pie(labels=status_labels, values=status_values)])
        status_fig.update_layout(title='Status Code Distribution')
        status_chart = json.dumps(status_fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        request_types = [row['request_type'] for row in request_data]
        request_counts = [row['count'] for row in request_data]
        request_fig = go.Figure(data=[go.Bar(x=request_types, y=request_counts)])
        request_fig.update_layout(title='Request Type Distribution')
        request_chart = json.dumps(request_fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        ip_addresses = [row['ip'] for row in ip_data]
        ip_counts = [row['count'] for row in ip_data]
        ip_fig = go.Figure(data=[go.Bar(x=ip_addresses, y=ip_counts)])
        ip_fig.update_layout(title='Top 10 IPs')
        ip_chart = json.dumps(ip_fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        apis = [row['api'] for row in api_data]
        api_counts = [row['count'] for row in api_data]
        api_fig = go.Figure(data=[go.Bar(x=apis, y=api_counts)])
        api_fig.update_layout(title='Top 5 APIs')
        api_chart = json.dumps(api_fig, cls=plotly.utils.PlotlyJSONEncoder)
        
        return render_template('dashboard.html', 
                              total_logs=total_logs, 
                              unique_ips=unique_ips, 
                              error_count=error_count,
                              files=files,
                              status_chart=status_chart,
                              request_chart=request_chart,
                              ip_chart=ip_chart,
                              api_chart=api_chart)
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash(f"Database error: {str(e)}", "danger")
        return render_template('dashboard.html')
    finally:
        conn.close()

@app.route('/logs')
def view_logs():
    """View parsed logs with filtering options"""
    # Get filter parameters
    file_name = request.args.get('file_name', '')
    status_code = request.args.get('status_code', '')
    ip = request.args.get('ip', '')
    request_type = request.args.get('request_type', '')
    page = request.args.get('page', 1, type=int)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Build query with filters
        query = 'SELECT * FROM logs WHERE 1=1'
        params = []
        
        if file_name:
            query += ' AND file_name = ?'
            params.append(file_name)
        
        if status_code:
            query += ' AND status_code = ?'
            params.append(int(status_code))
        
        if ip:
            query += ' AND ip LIKE ?'
            params.append(f'%{ip}%')
        
        if request_type:
            query += ' AND request_type = ?'
            params.append(request_type)
        
        # Get total count for pagination
        count_query = query.replace('SELECT *', 'SELECT COUNT(*)')
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Pagination
        per_page = 100
        offset = (page - 1) * per_page
        query += ' ORDER BY id DESC LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        # Get filter options
        cursor.execute('SELECT DISTINCT file_name FROM logs')
        file_names = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('SELECT DISTINCT status_code FROM logs')
        status_codes = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('SELECT DISTINCT request_type FROM logs')
        request_types = [row[0] for row in cursor.fetchall()]
        
        total_pages = (total_count + per_page - 1) // per_page
        
        return render_template('logs.html',
                              logs=logs,
                              file_names=file_names,
                              status_codes=status_codes,
                              request_types=request_types,
                              current_page=page,
                              total_pages=total_pages,
                              total_count=total_count,
                              filters={
                                  'file_name': file_name,
                                  'status_code': status_code,
                                  'ip': ip,
                                  'request_type': request_type
                              })
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        flash(f"Database error: {str(e)}", "danger")
        return render_template('logs.html',
                              logs=[],
                              file_names=[],
                              status_codes=[],
                              request_types=[],
                              current_page=1,
                              total_pages=0,
                              total_count=0,
                              filters={
                                  'file_name': file_name,
                                  'status_code': status_code,
                                  'ip': ip,
                                  'request_type': request_type
                              })
    finally:
        conn.close()

@app.route('/analytics')
def analytics():
    """Advanced analytics and visualizations using Dash"""
    # Redirect to the Dash app
    return redirect('/dash/')


@app.route('/delete_file/<file_name>')
def delete_file(file_name):
    """Delete a log file and its entries"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete logs for this file
        cursor.execute('DELETE FROM logs WHERE file_name = ?', (file_name,))
        
        # Delete file record
        cursor.execute('DELETE FROM files WHERE file_name = ?', (file_name,))
        
        conn.commit()
        conn.close()
        
        # Try to delete the actual file if it exists
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        flash(f'File {file_name} and all its logs have been deleted', 'success')
    except Exception as e:
        flash(f'Error deleting file: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/api/logs')
def api_logs():
    """API endpoint to get logs in JSON format"""
    file_name = request.args.get('file_name', '')
    status_code = request.args.get('status_code', '')
    ip = request.args.get('ip', '')
    request_type = request.args.get('request_type', '')
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Build query with filters
        query = 'SELECT * FROM logs WHERE 1=1'
        count_query = 'SELECT COUNT(*) FROM logs WHERE 1=1'
        params = []
        
        if file_name:
            query += ' AND file_name = ?'
            count_query += ' AND file_name = ?'
            params.append(file_name)
        
        if status_code:
            query += ' AND status_code = ?'
            count_query += ' AND status_code = ?'
            params.append(int(status_code) if status_code.isdigit() else status_code)
        
        if ip:
            query += ' AND ip LIKE ?'
            count_query += ' AND ip LIKE ?'
            params.append(f'%{ip}%')
        
        if request_type:
            query += ' AND request_type = ?'
            count_query += ' AND request_type = ?'
            params.append(request_type)
        
        # Get total count
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Get logs with limit
        query += ' ORDER BY timestamp DESC LIMIT 100'
        
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        # Convert to list of dicts
        result = []
        for log in logs:
            log_dict = {}
            for key in log.keys():
                log_dict[key] = log[key]
            result.append(log_dict)
        
        return jsonify({
            'logs': result,
            'total_count': total_count,
            'filters': {
                'file_name': file_name,
                'ip': ip,
                'status_code': status_code,
                'request_type': request_type
            }
        })
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/reset_data')
def reset_data():
    """Reset all log data in the system"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete all logs
        cursor.execute('DELETE FROM logs')
        
        # Delete all file records
        cursor.execute('DELETE FROM files')
        
        conn.commit()
        conn.close()
        
        # Delete all actual files in the uploads folder
        for file_name in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        flash('All log data has been successfully reset', 'success')
    except Exception as e:
        flash(f'Error resetting data: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    # Import and initialize Dash app
    from dash_app import create_dash_app
    create_dash_app(app)
    
    # Initialize database
    init_db()
    
    # Run the app
    app.run(host="0.0.0.0", port=5000, debug=True)
