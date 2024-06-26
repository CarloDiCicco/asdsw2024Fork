from flask import Flask, jsonify
import uuid

app = Flask(__name__)

@app.route('/generate/uuid', methods=['GET']) # here we define the route
def generate_uuid():
    id = uuid.uuid4().hex # Generate a random UUID 
    return jsonify({'uuid': id})

if __name__ == '__main__':
    # Run this multiple times on different ports: 5001, 5002, 5003, etc.
    app.run()
