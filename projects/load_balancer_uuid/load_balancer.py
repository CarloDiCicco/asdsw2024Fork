from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# List of backend servers
servers = [
    "http://localhost:5001/generate/uuid",
    "http://localhost:5002/generate/uuid",
    "http://localhost:5003/generate/uuid",
    "http://localhost:5004/generate/uuid"
]

current_server = 0

# Function to get the next server
def get_server():
    global current_server
    server = servers[current_server]
    current_server = (current_server + 1) % len(servers)
    return server

@app.route('/generate/uuid', methods=['GET'])
def generate_uuid():
    server_url = get_server() # Get the next server url 
    try:
        response = requests.get(server_url)
        if response.status_code == 200: # Check if the request was successful
            result = response.json() # Get the JSON data from the response
            result['server'] = server_url 
            return jsonify(result), 200 # Return the JSON data with the server URL
        else:
            return jsonify({'error': 'Failed to generate UUID', 'server': server_url}), 500
    except requests.exceptions.RequestException:
        return jsonify({'error': 'Backend server error', 'server': server_url}), 500

if __name__ == '__main__':
    app.run(debug=True)

