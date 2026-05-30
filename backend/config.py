import os

# El backend está en una subcarpeta, subimos un nivel para encontrar instance/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
INSTANCE_DB_PATH = os.path.join(BASE_DIR, 'instance', 'ferremas.db')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f"sqlite:///{INSTANCE_DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
