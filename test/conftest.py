import importlib
import os
import sys

import pytest


@pytest.fixture(scope='session')
def backend_app(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp('ferremas_db')
    db_path = tmp_dir / 'ferremas_test.db'
    os.environ['DATABASE_URL'] = f"sqlite:///{db_path}"

    if 'backend.app' in sys.modules:
        del sys.modules['backend.app']

    backend_app = importlib.import_module('backend.app')
    importlib.reload(backend_app)

    with backend_app.app.app_context():
        backend_app.db.create_all()

    return backend_app


@pytest.fixture
def backend_client(backend_app):
    return backend_app.app.test_client()
