from src.core.env_loader import load_environment_variables
load_environment_variables()

import json
import requests
import pymysql
import os

from src.core.security.token_validator import create_access_token
from src.core.constants import (
    JWT_EMAIL_CLAIM,
    JWT_FULL_NAME_CLAIM,
    JWT_LOCALE_CLAIM,
    JWT_ROLE_CLAIM,
    JWT_SUB_CLAIM,
    JWT_USER_ID_CLAIM,
)

conn = pymysql.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT')),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME'),
    cursorclass=pymysql.cursors.DictCursor,
)
with conn.cursor() as cur:
    cur.execute("SELECT id, username, email, full_name, role FROM users WHERE username=%s", ('venkata.janga',))
    user = cur.fetchone()
conn.close()

payload = {
    JWT_SUB_CLAIM: user['username'],
    JWT_USER_ID_CLAIM: user['id'],
    JWT_ROLE_CLAIM: user['role'],
    JWT_EMAIL_CLAIM: user['email'],
    JWT_FULL_NAME_CLAIM: user.get('full_name') or '',
    JWT_LOCALE_CLAIM: 'en',
}

token = create_access_token(payload)
headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json',
}

start_resp = requests.post(
    'http://127.0.0.1:8000/chat',
    headers=headers,
    data=json.dumps({'message': 'start', 'session_id': 'default-session'}),
    timeout=20,
)
start_resp.raise_for_status()
start_data = start_resp.json()
print('start_status', start_resp.status_code)
print('session_id', start_data.get('session_id'))
print('start_trace', start_data.get('trace'))

chat_resp = requests.post(
    'http://127.0.0.1:8000/chat',
    headers=headers,
    data=json.dumps({'message': 'I am a Python developer with 5 years experience', 'session_id': start_data['session_id']}),
    timeout=20,
)
chat_resp.raise_for_status()
chat_data = chat_resp.json()
print('chat_status', chat_resp.status_code)
print('chat_trace', chat_data.get('trace'))
print('bot', chat_data.get('bot') or chat_data.get('followup_question') or chat_data.get('message'))
