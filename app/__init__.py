from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class='app.config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialisation des extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import des routes dans le contexte
    with app.app_context():
        from app.routes import bp as main_bp
        app.register_blueprint(main_bp)
        
        # Création des tables si nécessaire
        db.create_all()
    
    return app