import csv
import json
import requests
from datetime import datetime
from collections import defaultdict

# Configuration
DYNATRACE_ENV_URL = "https://fzq57782.live.dynatrace.com"
DYNATRACE_API_TOKEN = ""
CSV_FILE_PATH = "yarnalerting.csv"

def read_and_organize_csv(csv_file):
    """Read CSV and organize by yarn_queue"""
    
    queue_data = defaultdict(list)
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            queue_name = row.get("yarn_queue", "unknown")
            queue_data[queue_name].append(row)
    
    return queue_data

def send_logs_by_queue(queue_data):
    """Send logs organized by queue, each queue gets its own logger source"""
    
    url = f"{DYNATRACE_ENV_URL}/api/v2/logs/ingest"
    
    headers = {
        "Authorization": f"Api-Token {DYNATRACE_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    total_logs = 0
    
    # Process each queue separately
    for queue_name, records in sorted(queue_data.items()):
        print(f"\n{'='*60}")
        print(f"Processing Queue: {queue_name} ({len(records)} records)")
        print(f"{'='*60}")
        
        logs = []
        
        for record in records:
            log_entry = {
                "content": json.dumps(record),  # Send full record as JSON
                "severity": "INFO",
                "timestamp": int(datetime.now().timestamp() * 1000),
                "attributes": {
                    "yarn_queue": queue_name,
                    "dy_mail_reference": record.get("Dy_Mail_DL", ""),
                    "customer": record.get("customer", ""),
                    "remedy_queue": record.get("Remedy_Queue", ""),
                    "third_threshold": record.get("Third_Threshold", ""),
                },
                "dl.source": f"yarn_queue_{queue_name}"  # Source identifier
            }
            logs.append(log_entry)
        
        # Send batch for this queue
        batch_size = 50
        for i in range(0, len(logs), batch_size):
            batch = logs[i:i + batch_size]
            payload = {"logs": batch}
            
            try:
                batch_num = (i // batch_size) + 1
                print(f"  Sending batch {batch_num} ({len(batch)} logs)...", end=" ")
                
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                
                if response.status_code in [200, 204]:
                    print(f"✓")
                    total_logs += len(batch)
                else:
                    print(f"✗ Status: {response.status_code}")
                    print(f"    Response: {response.text[:200]}")
                    
            except requests.exceptions.RequestException as e:
                print(f"✗ Error: {e}")
                return None
        
        print(f"  ✓ Queue '{queue_name}' completed ({len(logs)} total)")
    
    return total_logs

def generate_dql_queries(queue_data):
    """Generate DQL queries for each queue"""
    
    print(f"\n{'='*60}")
    print("DQL QUERIES FOR EACH QUEUE")
    print(f"{'='*60}\n")
    
    print("# Query all queues summary:")
    print("fetch logs")
    print('| filter contains(dl.source, "yarn_queue_")')
    print("| summarize count()\n")
    
    print("# Individual queue queries:\n")
    
    for queue_name in sorted(queue_data.keys()):
        print(f"# {queue_name}:")
        print(f'fetch logs | filter attributes["yarn_queue"] == "{queue_name}"')
        print(f"| summarize count()")
        print(f"# Total records: {len(queue_data[queue_name])}\n")

def generate_dashboard_config(queue_data):
    """Generate dashboard configuration"""
    
    print(f"\n{'='*60}")
    print("DASHBOARD WIDGET QUERIES")
    print(f"{'='*60}\n")
    
    print("1. Total records ingested:")
    print('fetch logs | filter contains(dl.source, "yarn_queue_")\n')
    
    print("2. View all logs with key fields:")
    print('fetch logs | filter contains(dl.source, "yarn_queue_")')
    print('| fields timestamp, content\n')
    
    print("3. Logs for CPS queue:")
    print('fetch logs | filter dl.source == "yarn_queue_cps"\n')
    
    print("4. Logs for all queues - grouped by source:")
    print('fetch logs | filter contains(dl.source, "yarn_queue_")')
    print('| fields dl.source\n')

def main():
    print("\n" + "="*60)
    print("Dynatrace CSV Ingestion - Organized by Queue")
    print("="*60 + "\n")
    
    # Step 1: Read and organize CSV
    print("Step 1: Reading CSV and organizing by queue...")
    queue_data = read_and_organize_csv(CSV_FILE_PATH)
    
    print(f"✓ Found {len(queue_data)} unique queues")
    for queue_name, records in sorted(queue_data.items()):
        print(f"  - {queue_name}: {len(records)} records")
    
    # Step 2: Send data
    print("\nStep 2: Sending data to Dynatrace...")
    total = send_logs_by_queue(queue_data)
    
    if total:
        print(f"\n{'='*60}")
        print(f"✓ SUCCESS! Ingested {total} total log entries")
        print(f"{'='*60}")
        
        # Generate queries
        generate_dql_queries(queue_data)
        generate_dashboard_config(queue_data)
        
        print(f"\n{'='*60}")
        print("NEXT STEPS:")
        print(f"{'='*60}")
        print("1. Go to Dynatrace Logs")
        print("2. Click 'DQL' button")
        print("3. Copy one of the queries above")
        print("4. Run the query to see your data")
        print("5. Create dashboard widgets from queries")
        print("6. Set up alerts based on queue/threshold conditions\n")
        
    else:
        print("\n✗ Ingestion failed")

if __name__ == "__main__":
    main()