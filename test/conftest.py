import importlib
import os
import sys

import pytest


@pytest.fixture(scope='function')
def backend_app(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp('ferremas_db')
    db_path = tmp_dir / 'ferremas_test.db'
    os.environ['DATABASE_URL'] = f"sqlite:///{db_path}"

    for module_name in list(sys.modules):
        if module_name == 'backend.app' or module_name == 'backend' or module_name.startswith('backend.'):
            del sys.modules[module_name]
        if module_name in ('models', 'config'):
            del sys.modules[module_name]

    backend_app = importlib.import_module('backend.app')
    importlib.reload(backend_app)

    with backend_app.app.app_context():
        backend_app.db.create_all()

    return backend_app


@pytest.fixture
def backend_client(backend_app):
    return backend_app.app.test_client()
