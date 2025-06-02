from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from flask_jwt_extended import (
    JWTManager
)
from flask_caching import Cache
import os
load_dotenv()
import logging

app = Flask(__name__)

cors = CORS(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
host = os.environ.get('DB_HOST')
password = os.environ.get('DB_PASSWORD')
secret_key = os.environ.get('SECRET_KEY')

app.config['CORS_HEADERS'] = 'Content-Type'
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['JWT_SECRET_KEY'] = secret_key 
jwt = JWTManager(app)



app.debug = True

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)


db_config = {
    'host': host,
    'port': 3308,
    'database': 'historial_medico',
    'user': 'root',
    'password': password
}

import medicamentos, diagnosticos, roles, medicos, citas, tratamientos, usuarios, auth, historialMedico, paciente