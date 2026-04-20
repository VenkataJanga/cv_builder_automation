from src.core.env_loader import load_environment_variables
load_environment_variables()

import json
import os
import pymysql
import requests

from src.core.constants import (
    JWT_EMAIL_CLAIM,
    JWT_FULL_NAME_CLAIM,
    JWT_LOCALE_CLAIM,
    JWT_ROLE_CLAIM,
    JWT_SUB_CLAIM,
    JWT_USER_ID_CLAIM,
)
from src.core.security.token_validator import create_access_token


def get_user():
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
    return user


def make_headers(user):
    token = create_access_token({
        JWT_SUB_CLAIM: user['username'],
        JWT_USER_ID_CLAIM: user['id'],
        JWT_ROLE_CLAIM: user['role'],
        JWT_EMAIL_CLAIM: user['email'],
        JWT_FULL_NAME_CLAIM: user.get('full_name') or '',
        JWT_LOCALE_CLAIM: 'en',
    })
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}


def post_chat(headers, message, session_id='default-session'):
    response = requests.post(
        'http://127.0.0.1:8000/chat',
        headers=headers,
        data=json.dumps({'message': message, 'session_id': session_id}),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


user = get_user()
headers = make_headers(user)
start = post_chat(headers, 'start')
session_id = start['session_id']
print('session_id', session_id)
print('q1', start.get('bot') or start.get('question'))

answers = [
    'Venkata Janga',
    'Senior Python Developer',
    'EMP12345',
    'venkata.janga@cvbuilder.local',
    'Bengaluru',
    'Experienced Python developer specializing in backend systems and APIs.',
    '8 years',
    'Python, FastAPI, SQL, Azure',
    'Designed scalable APIs and led backend integrations.',
    'Banking and insurance domains.',
    'Led a small engineering team and mentored developers.',
    'Improved processing speed by 35 percent.',
]

result = start
for idx, answer in enumerate(answers, start=1):
    result = post_chat(headers, answer, session_id)
    prompt = result.get('bot') or result.get('followup_question') or result.get('question') or result.get('message')
    print(f'answer_{idx}', answer)
    print('next', prompt)
    if result.get('trace'):
        print('trace', result['trace'])
        break

print('final_response_keys', sorted(result.keys()))
