from flask import Flask, request, jsonify, render_template, session
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import time

app = Flask(__name__, template_folder='.')
app.secret_key = os.urandom(24) # Chave de segurança extrema para sessões
socketio = SocketIO(app, cors_allowed_origins="*")

DATA_FILE = 'Datastore.json'

# --- BANCO DE DADOS E CONTAS PADRÃO ---
def load_db():
    if not os.path.exists(DATA_FILE):
        # Criação das contas padrão (Senhas Criptografadas)
        initial_data = {
            "antvkzin": {"password": generate_password_hash("@A7953721896"), "tag": "Fundador", "color": "blue", "pfp": "Perfil1.png", "bio": ""},
            "kzzezay": {"password": generate_password_hash("K7953721896ZZ"), "tag": "Sub-Fundador", "color": "darkred", "pfp": "Perfil1.png", "bio": ""},
            "Mod1": {"password": generate_password_hash("modsenha1"), "tag": "Moderador", "color": "orange", "pfp": "Perfil1.png", "bio": ""},
            "Mod2": {"password": generate_password_hash("modsenha2"), "tag": "Moderador", "color": "orange", "pfp": "Perfil1.png", "bio": ""},
            "SunlixyZ": {"password": generate_password_hash("Keijo13579"), "tag": "Helper", "color": "purple", "pfp": "Perfil1.png", "bio": ""}
        }
        save_db(initial_data)
        return initial_data
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_db(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

db = load_db()

# Dicionário de IPs banidos/mutados temporariamente (Auto-Moderação)
banned_ips = {}

# --- ROTAS DA WEB ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth', methods=['POST'])
def auth():
    data = request.json
    action = data.get('action')
    username = data.get('username')
    password = data.get('password')

    if action == 'register':
        if username in db:
            return jsonify({"status": "error", "message": "Essa conta já existe no sistema!"})
        
        db[username] = {
            "password": generate_password_hash(password),
            "tag": "Membro",
            "color": "gray",
            "pfp": "Perfil1.png",
            "bio": ""
        }
        save_db(db)
        return jsonify({"status": "success", "message": "Conta criada com sucesso!"})

    elif action == 'login':
        user = db.get(username)
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return jsonify({"status": "success", "user": {"username": username, "tag": user['tag'], "color": user['color'], "pfp": user['pfp']}})
        return jsonify({"status": "error", "message": "Usuário ou senha incorretos."})

@app.route('/delete_account', methods=['POST'])
def delete_account():
    data = request.json
    username = session.get('username')
    password = data.get('password')

    if not username: return jsonify({"status": "error", "message": "Não autenticado."})
    
    user = db.get(username)
    if user['tag'] in ['Fundador', 'Sub-Fundador', 'Moderador', 'Helper']:
        return jsonify({"status": "error", "message": "Aviso: Esta conta de administrador não pode ser excluída do sistema."})
    
    if check_password_hash(user['password'], password):
        del db[username]
        save_db(db)
        session.pop('username', None)
        return jsonify({"status": "success", "message": "Conta deletada."})
    return jsonify({"status": "error", "message": "Senha incorreta."})

# --- WEBSOCKETS (CHAT GLOBAL & COMANDOS) ---
@socketio.on('send_message')
def handle_message(data):
    username = session.get('username')
    if not username: return
    
    client_ip = request.remote_addr
    # Checagem de Ban/Kick por IP (Segurança)
    if client_ip in banned_ips and banned_ips[client_ip] > time.time():
        emit('server_message', {'msg': 'Você está mutado/kickado temporariamente.'}, room=request.sid)
        return

    user_info = db[username]
    msg_text = data.get('message', '')

    # Sistema de Comandos Básicos para Admins
    if msg_text.startswith('/'):
        role = user_info['tag']
        if role in ['Fundador', 'Sub-Fundador'] and msg_text.startswith('/kick'):
            emit('server_message', {'msg': 'Comando de Kick executado (Simulação)'}, room=request.sid)
            return

    # Envia a mensagem para todos na sala
    emit('receive_message', {
        'username': username,
        'tag': user_info['tag'],
        'color': user_info['color'],
        'pfp': user_info['pfp'],
        'text': msg_text
    }, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)