from main_app import create_app, db
from main_app.extensions import migrate
from flask_migrate import Migrate

app = create_app()
migrate.init_app(app, db)

if __name__ == "__main__":
    app.run(debug=True)
