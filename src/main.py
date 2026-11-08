from flask import Flask

from controllers.instituicao_ensino_controller import instituicao_ensino_bp
from controllers.usuario_controller import usuario_bp
from helpers.database import inicializar_banco
from helpers.environment import FLASK_DEBUG, FLASK_PORT
from helpers.erros import registrar_handlers


def create_app():
    inicializar_banco()

    app = Flask(__name__)
    app.register_blueprint(instituicao_ensino_bp)
    app.register_blueprint(usuario_bp)
    registrar_handlers(app)
    return app


if __name__ == "__main__":
    create_app().run(port=FLASK_PORT, debug=FLASK_DEBUG)
