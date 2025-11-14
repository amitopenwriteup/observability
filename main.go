package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"
)

// DataRecord represents a single ingested data record
type DataRecord struct {
	ID        int                    `json:"id"`
	Timestamp string                 `json:"timestamp"`
	Data      map[string]interface{} `json:"data"`
}

// Simple in-memory storage
var records []DataRecord
var recordCounter = 0

func main() {
	// Setup routes
	http.HandleFunc("/", homeHandler)
	http.HandleFunc("/api/ingest", ingestHandler)
	http.HandleFunc("/api/records", recordsHandler)

	// Start server
	port := ":8080"
	fmt.Printf("🚀 Server starting on http://localhost%s\n", port)
	fmt.Println("📝 Visit http://localhost:8080 to use the app")
	log.Fatal(http.ListenAndServe(port, nil))
}

// homeHandler serves the HTML frontend
func homeHandler(w http.ResponseWriter, r *http.Request) {
	html := `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Data Ingestion App</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        .section {
            margin: 30px 0;
        }
        label {
            display: block;
            margin: 10px 0 5px;
            font-weight: bold;
            color: #555;
        }
        input, textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        button {
            background: #4CAF50;
            color: white;
            padding: 12px 25px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
        }
        button:hover {
            background: #45a049;
        }
        .message {
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
            display: none;
        }
        .success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin: 20px 0;
        }
        .stat-box {
            flex: 1;
            background: #4CAF50;
            color: white;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
        }
        .stat-box h2 {
            margin: 0;
            font-size: 36px;
        }
        .stat-box p {
            margin: 5px 0 0;
        }
        .records-list {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            border-radius: 5px;
            background: #f9f9f9;
        }
        .record {
            background: white;
            padding: 10px;
            margin: 5px 0;
            border-left: 3px solid #4CAF50;
            border-radius: 3px;
        }
        pre {
            background: #f4f4f4;
            padding: 10px;
            border-radius: 3px;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Simple Data Ingestion App</h1>
        
        <div class="stats">
            <div class="stat-box">
                <h2 id="recordCount">0</h2>
                <p>Total Records</p>
            </div>
        </div>

        <!-- JSON Ingestion Section -->
        <div class="section">
            <h2>📥 Ingest JSON Data</h2>
            <p style="color: #666;">Send data in JSON format to be stored.</p>
            
            <label>Name:</label>
            <input type="text" id="name" placeholder="Enter name">
            
            <label>Email:</label>
            <input type="text" id="email" placeholder="Enter email">
            
            <label>Age:</label>
            <input type="number" id="age" placeholder="Enter age">
            
            <button onclick="ingestData()">Submit Data</button>
            
            <div id="message" class="message"></div>
        </div>

        <!-- CSV Upload Section -->
        <div class="section">
            <h2>📄 Upload CSV File</h2>
            <p style="color: #666;">Upload a CSV file (columns: name, email, age)</p>
            
            <input type="file" id="csvFile" accept=".csv">
            <button onclick="uploadCSV()">Upload CSV</button>
            
            <div id="csvMessage" class="message"></div>
        </div>

        <!-- View Records Section -->
        <div class="section">
            <h2>📋 Stored Records</h2>
            <button onclick="loadRecords()">Refresh Records</button>
            <div id="recordsList" class="records-list"></div>
        </div>
    </div>

    <script>
        // Load initial stats
        loadRecords();

        // Ingest individual JSON data
        async function ingestData() {
            const name = document.getElementById('name').value;
            const email = document.getElementById('email').value;
            const age = document.getElementById('age').value;

            if (!name || !email || !age) {
                showMessage('message', 'Please fill all fields', 'error');
                return;
            }

            const data = { name, email, age: parseInt(age) };

            try {
                const response = await fetch('/api/ingest', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                
                if (response.ok) {
                    showMessage('message', 'Data ingested successfully!', 'success');
                    document.getElementById('name').value = '';
                    document.getElementById('email').value = '';
                    document.getElementById('age').value = '';
                    loadRecords();
                } else {
                    showMessage('message', 'Error: ' + result.error, 'error');
                }
            } catch (error) {
                showMessage('message', 'Network error: ' + error.message, 'error');
            }
        }

        // Upload and ingest CSV
        async function uploadCSV() {
            const fileInput = document.getElementById('csvFile');
            const file = fileInput.files[0];

            if (!file) {
                showMessage('csvMessage', 'Please select a CSV file', 'error');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/api/ingest?format=csv', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (response.ok) {
                    showMessage('csvMessage', 'Successfully ingested ' + result.count + ' records!', 'success');
                    fileInput.value = '';
                    loadRecords();
                } else {
                    showMessage('csvMessage', 'Error: ' + result.error, 'error');
                }
            } catch (error) {
                showMessage('csvMessage', 'Network error: ' + error.message, 'error');
            }
        }

        // Load and display records
        async function loadRecords() {
            try {
                const response = await fetch('/api/records');
                const data = await response.json();
                
                document.getElementById('recordCount').textContent = data.count;
                
                const recordsList = document.getElementById('recordsList');
                if (data.count === 0) {
                    recordsList.innerHTML = '<p>No records yet. Add some data!</p>';
                } else {
                    recordsList.innerHTML = data.records.map(record => 
                        '<div class="record">' +
                            '<strong>ID:</strong> ' + record.id + ' | ' +
                            '<strong>Time:</strong> ' + record.timestamp +
                            '<pre>' + JSON.stringify(record.data, null, 2) + '</pre>' +
                        '</div>'
                    ).join('');
                }
            } catch (error) {
                console.error('Error loading records:', error);
            }
        }

        // Show message helper
        function showMessage(elementId, text, type) {
            const messageEl = document.getElementById(elementId);
            messageEl.textContent = text;
            messageEl.className = 'message ' + type;
            messageEl.style.display = 'block';
            setTimeout(() => {
                messageEl.style.display = 'none';
            }, 5000);
        }
    </script>
</body>
</html>`
	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(html))
}

// ingestHandler handles data ingestion (JSON or CSV)
func ingestHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	w.Header().Set("Content-Type", "application/json")

	// Check if CSV upload
	if r.URL.Query().Get("format") == "csv" {
		handleCSVUpload(w, r)
		return
	}

	// Handle JSON ingestion
	var data map[string]interface{}
	if err := json.NewDecoder(r.Body).Decode(&data); err != nil {
		json.NewEncoder(w).Encode(map[string]string{"error": "Invalid JSON"})
		return
	}

	// Create new record
	recordCounter++
	record := DataRecord{
		ID:        recordCounter,
		Timestamp: time.Now().Format("2006-01-02 15:04:05"),
		Data:      data,
	}

	records = append(records, record)

	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"id":      record.ID,
		"message": "Data ingested successfully",
	})

	log.Printf("✓ Ingested record #%d: %v\n", record.ID, data)
}

// handleCSVUpload processes CSV file uploads
func handleCSVUpload(w http.ResponseWriter, r *http.Request) {
	file, _, err := r.FormFile("file")
	if err != nil {
		json.NewEncoder(w).Encode(map[string]string{"error": "Failed to read file"})
		return
	}
	defer file.Close()

	reader := csv.NewReader(file)
	headers, err := reader.Read() // Read header row
	if err != nil {
		json.NewEncoder(w).Encode(map[string]string{"error": "Invalid CSV format"})
		return
	}

	count := 0
	for {
		row, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			continue
		}

		// Create data map from CSV row
		data := make(map[string]interface{})
		for i, value := range row {
			if i < len(headers) {
				data[headers[i]] = value
			}
		}

		recordCounter++
		record := DataRecord{
			ID:        recordCounter,
			Timestamp: time.Now().Format("2006-01-02 15:04:05"),
			Data:      data,
		}

		records = append(records, record)
		count++
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"count":   count,
		"message": fmt.Sprintf("Ingested %d records from CSV", count),
	})

	log.Printf("✓ Ingested %d records from CSV\n", count)
}

// recordsHandler returns all stored records
func recordsHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	
	json.NewEncoder(w).Encode(map[string]interface{}{
		"count":   len(records),
		"records": records,
	})
}