#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Avaliação TeleCIMENTO - Backend Flask
Versão 4.0 - API para gerenciamento de avaliações
"""

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import pytz
import sqlite3
from contextlib import contextmanager
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Permitir CORS para todas as rotas

# Configurações
DATABASE_FILE = 'telecimento_avaliacoes.db'
TIMEZONE = pytz.timezone('America/Sao_Paulo')

class DatabaseManager:
    """Gerenciador de banco de dados SQLite"""
    
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Inicializar tabelas do banco de dados"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela de avaliações
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS avaliacoes (
                    id TEXT PRIMARY KEY,
                    dispositivo_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    avaliacao_geral TEXT NOT NULL,
                    setores TEXT,
                    feedback TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de controle de votação
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS controle_votacao (
                    dispositivo_id TEXT PRIMARY KEY,
                    ultimo_voto TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de logs do sistema
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS logs_sistema (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    acao TEXT NOT NULL,
                    detalhes TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            logger.info("Banco de dados inicializado com sucesso")
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexões com o banco"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

# Instanciar gerenciador de banco
db_manager = DatabaseManager(DATABASE_FILE)

def get_brazil_time():
    """Obter horário atual do Brasil"""
    return datetime.now(TIMEZONE)

def is_same_day(date1, date2):
    """Verificar se duas datas são do mesmo dia"""
    return date1.date() == date2.date()

@app.route('/')
def index():
    """Página inicial com informações da API"""
    html = '''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>API TeleCIMENTO - Sistema de Avaliação</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
                color: #ffffff;
                margin: 0;
                padding: 2rem;
                min-height: 100vh;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 15px;
                padding: 2rem;
                backdrop-filter: blur(10px);
            }
            h1 {
                color: #FFD700;
                text-align: center;
                margin-bottom: 2rem;
            }
            .endpoint {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 215, 0, 0.3);
                border-radius: 10px;
                padding: 1rem;
                margin-bottom: 1rem;
            }
            .method {
                display: inline-block;
                padding: 0.25rem 0.5rem;
                border-radius: 5px;
                font-weight: bold;
                margin-right: 1rem;
            }
            .get { background: #4CAF50; }
            .post { background: #2196F3; }
            .delete { background: #f44336; }
            .status {
                text-align: center;
                padding: 1rem;
                background: rgba(76, 175, 80, 0.2);
                border-radius: 10px;
                margin-bottom: 2rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏗️ API TeleCIMENTO - Sistema de Avaliação</h1>
            
            <div class="status">
                <h3>✅ API Online e Funcionando</h3>
                <p>Horário do servidor: {{ current_time }}</p>
            </div>
            
            <h2>📋 Endpoints Disponíveis</h2>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/evaluations</strong>
                <p>Obter todas as avaliações</p>
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/submit-evaluation</strong>
                <p>Enviar nova avaliação</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/check-vote/&lt;dispositivo_id&gt;</strong>
                <p>Verificar se dispositivo já votou hoje</p>
            </div>
            
            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/reset-timer</strong>
                <p>Resetar timer de votação (admin)</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/statistics</strong>
                <p>Obter estatísticas gerais</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/health</strong>
                <p>Verificar saúde da API</p>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(html, current_time=get_brazil_time().strftime('%d/%m/%Y %H:%M:%S'))

@app.route('/api/health')
def health_check():
    """Verificar saúde da API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': get_brazil_time().isoformat(),
        'database': 'connected'
    })

@app.route('/api/evaluations', methods=['GET'])
def get_evaluations():
    """Obter todas as avaliações"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, dispositivo_id, timestamp, avaliacao_geral, setores, feedback
                FROM avaliacoes
                ORDER BY timestamp DESC
            ''')
            
            evaluations = []
            for row in cursor.fetchall():
                evaluation = {
                    'id': row['id'],
                    'dispositivoId': row['dispositivo_id'],
                    'timestamp': row['timestamp'],
                    'avaliacaoGeral': row['avaliacao_geral'],
                    'setores': json.loads(row['setores']) if row['setores'] else {},
                    'feedback': row['feedback'] or ''
                }
                evaluations.append(evaluation)
            
            return jsonify({
                'success': True,
                'evaluations': evaluations,
                'total': len(evaluations)
            })
    
    except Exception as e:
        logger.error(f"Erro ao obter avaliações: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/submit-evaluation', methods=['POST'])
def submit_evaluation():
    """Enviar nova avaliação"""
    try:
        data = request.get_json()
        
        # Validar dados obrigatórios
        required_fields = ['id', 'dispositivoId', 'timestamp', 'avaliacaoGeral']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório ausente: {field}'
                }), 400
        
        # Verificar se já votou hoje
        dispositivo_id = data['dispositivoId']
        if has_voted_today(dispositivo_id):
            return jsonify({
                'success': False,
                'error': 'Dispositivo já votou hoje'
            }), 409
        
        # Salvar avaliação
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO avaliacoes (id, dispositivo_id, timestamp, avaliacao_geral, setores, feedback)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data['id'],
                data['dispositivoId'],
                data['timestamp'],
                data['avaliacaoGeral'],
                json.dumps(data.get('setores', {})),
                data.get('feedback', '')
            ))
            
            # Atualizar controle de votação
            cursor.execute('''
                INSERT OR REPLACE INTO controle_votacao (dispositivo_id, ultimo_voto, updated_at)
                VALUES (?, ?, ?)
            ''', (
                dispositivo_id,
                data['timestamp'],
                get_brazil_time().isoformat()
            ))
            
            conn.commit()
        
        # Log da ação
        log_action('AVALIACAO_ENVIADA', f'Dispositivo: {dispositivo_id}, Avaliação: {data["avaliacaoGeral"]}')
        
        logger.info(f"Avaliação salva: {data['id']} - {data['avaliacaoGeral']}")
        
        return jsonify({
            'success': True,
            'message': 'Avaliação salva com sucesso',
            'id': data['id']
        })
    
    except Exception as e:
        logger.error(f"Erro ao salvar avaliação: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/check-vote/<dispositivo_id>', methods=['GET'])
def check_vote(dispositivo_id):
    """Verificar se dispositivo já votou hoje"""
    try:
        has_voted = has_voted_today(dispositivo_id)
        
        return jsonify({
            'success': True,
            'dispositivoId': dispositivo_id,
            'hasVotedToday': has_voted,
            'timestamp': get_brazil_time().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Erro ao verificar voto: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/reset-timer', methods=['POST'])
def reset_timer():
    """Resetar timer de votação (limpar todos os votos do dia)"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Limpar controle de votação
            cursor.execute('DELETE FROM controle_votacao')
            
            conn.commit()
        
        # Log da ação
        log_action('TIMER_RESETADO', 'Timer de votação resetado manualmente')
        
        logger.info("Timer de votação resetado")
        
        return jsonify({
            'success': True,
            'message': 'Timer resetado com sucesso',
            'timestamp': get_brazil_time().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Erro ao resetar timer: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """Obter estatísticas gerais"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total de avaliações
            cursor.execute('SELECT COUNT(*) as total FROM avaliacoes')
            total_avaliacoes = cursor.fetchone()['total']
            
            # Avaliações de hoje
            hoje = get_brazil_time().date().isoformat()
            cursor.execute('''
                SELECT COUNT(*) as total FROM avaliacoes 
                WHERE DATE(timestamp) = ?
            ''', (hoje,))
            avaliacoes_hoje = cursor.fetchone()['total']
            
            # Distribuição de avaliações
            cursor.execute('''
                SELECT avaliacao_geral, COUNT(*) as count 
                FROM avaliacoes 
                GROUP BY avaliacao_geral
            ''')
            distribuicao = {row['avaliacao_geral']: row['count'] for row in cursor.fetchall()}
            
            # Feedbacks com texto
            cursor.execute('''
                SELECT COUNT(*) as total FROM avaliacoes 
                WHERE feedback IS NOT NULL AND feedback != ""
            ''')
            total_feedbacks = cursor.fetchone()['total']
            
            return jsonify({
                'success': True,
                'statistics': {
                    'totalAvaliacoes': total_avaliacoes,
                    'avaliacoesHoje': avaliacoes_hoje,
                    'distribuicao': distribuicao,
                    'totalFeedbacks': total_feedbacks,
                    'timestamp': get_brazil_time().isoformat()
                }
            })
    
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def has_voted_today(dispositivo_id):
    """Verificar se dispositivo já votou hoje"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ultimo_voto FROM controle_votacao 
                WHERE dispositivo_id = ?
            ''', (dispositivo_id,))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            ultimo_voto = datetime.fromisoformat(result['ultimo_voto'].replace('Z', '+00:00'))
            hoje = get_brazil_time()
            
            return is_same_day(ultimo_voto, hoje)
    
    except Exception as e:
        logger.error(f"Erro ao verificar voto do dia: {e}")
        return False

def log_action(acao, detalhes=None):
    """Registrar ação no log do sistema"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO logs_sistema (acao, detalhes, timestamp)
                VALUES (?, ?, ?)
            ''', (acao, detalhes, get_brazil_time().isoformat()))
            conn.commit()
    except Exception as e:
        logger.error(f"Erro ao registrar log: {e}")

@app.errorhandler(404)
def not_found(error):
    """Handler para erro 404"""
    return jsonify({
        'success': False,
        'error': 'Endpoint não encontrado',
        'available_endpoints': [
            '/api/health',
            '/api/evaluations',
            '/api/submit-evaluation',
            '/api/check-vote/<dispositivo_id>',
            '/api/reset-timer',
            '/api/statistics'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    """Handler para erro 500"""
    return jsonify({
        'success': False,
        'error': 'Erro interno do servidor'
    }), 500

if __name__ == '__main__':
    # Log de inicialização
    log_action('SISTEMA_INICIADO', 'API Flask iniciada')
    
    print("🏗️ TeleCIMENTO - Sistema de Avaliação")
    print("=" * 50)
    print(f"📅 Data/Hora: {get_brazil_time().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🗄️ Banco de dados: {DATABASE_FILE}")
    print("🌐 Servidor iniciando...")
    print("=" * 50)
    
    # Executar aplicação
    app.run(
        host='0.0.0.0',  # Permitir acesso externo
        port=5000,
        debug=True,
        threaded=True
    )

