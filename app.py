import hmac
import hashlib
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
load_dotenv()

app = Flask(__name__)

GITHUB_SECRET = os.getenv('GITHUB_SECRET')
CHANGES_ROUTE_URL = 'http://localhost:8000/changes'

def verify_signature(payload, signature):
    mac = hmac.new(GITHUB_SECRET.encode(), msg=payload, digestmod=hashlib.sha1)
    return hmac.compare_digest('sha1=' + mac.hexdigest(), signature)

@app.route('/github-webhook', methods=['GET', 'POST', 'PUT', 'DELETE'])
def github_webhook():
    if GITHUB_SECRET is None:
        raise ValueError("GITHUB_SECRET environment variable is not set")
    
    payload = request.get_data()
    signature = request.headers.get('X-Hub-Signature')

    if not signature:
        return jsonify({'error': 'Missing signature header'}), 400

    event = request.headers.get('X-GitHub-Event')
    if not event:
        return jsonify({'error': 'Missing GitHub event header'}), 400

    if not verify_signature(payload, signature):
        return jsonify({'error': 'Invalid signature'}), 400
    signature = request.headers.get('X-Hub-Signature')

    event = request.headers.get('X-GitHub-Event')
    if event == 'pull_request':
        data = request.json
        if not data:
            return jsonify({'error': 'Invalid JSON payload'}), 400

        if data['action'] == 'closed' and data['pull_request']['merged']:
            pr_number = data['pull_request']['number']
            repo_full_name = data['repository']['full_name']
            diff_url = data['pull_request']['diff_url']

            # Get the diff of the merged PR
            diff_response = requests.get(diff_url)
            if diff_response.status_code == 200:
                diff = diff_response.text

                changes_request_data = {
                    'code_repo_id': repo_full_name,
                    'docs_repo_id': 'your_docs_repo_id',
                    'diffs': diff
                }

                print("changes request data: ", changes_request_data)
                # Send the diff to the /changes route
                changes_response = requests.post(CHANGES_ROUTE_URL, json=changes_request_data)
                if changes_response.status_code == 200:
                    return jsonify({'status': 'success'}), 200
                else:
                    return jsonify({'error': 'Failed to send diff to /changes'}), 500
            else:
                return jsonify({'error': 'Failed to get PR diff'}), 500

    return jsonify({'status': 'ignored'}), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)