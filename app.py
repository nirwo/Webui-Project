from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import logging
import os
import csv
import io
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_url_path='', static_folder='static')

# Configure CORS
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:8000", "http://127.0.0.1:8000"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": True
    }
})

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'shutdown_manager.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Models
class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner = db.Column(db.String(100), nullable=False)
    web_ui = db.Column(db.String(200))
    db_port = db.Column(db.Integer)
    status = db.Column(db.String(50), default='active')
    shutdown_verified = db.Column(db.Boolean, default=False)
    servers = db.relationship('Server', backref='application', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'owner': self.owner,
            'web_ui': self.web_ui,
            'db_port': self.db_port,
            'status': self.status,
            'shutdown_verified': self.shutdown_verified,
            'servers': [server.to_dict() for server in self.servers]
        }

class Server(db.Model):
    __tablename__ = 'servers'
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(15), nullable=False)
    ping_status = db.Column(db.Boolean, default=True)
    app_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'ping_status': self.ping_status,
            'app_id': self.app_id
        }

# Create tables
with app.app_context():
    try:
        logger.info("Creating database tables...")
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")
        raise

@app.route('/api/applications', methods=['GET'])
def get_applications():
    try:
        logger.debug("Fetching all applications")
        apps = Application.query.all()
        result = [app.to_dict() for app in apps]
        logger.debug(f"Found {len(result)} applications")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_applications: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/applications', methods=['POST'])
def create_application():
    try:
        data = request.json
        logger.debug(f"Creating new application with data: {data}")
        new_app = Application(
            name=data['name'],
            owner=data['owner'],
            web_ui=data.get('web_ui'),
            db_port=data.get('db_port')
        )
        db.session.add(new_app)
        db.session.commit()
        logger.info(f"Application created successfully with id: {new_app.id}")
        return jsonify({'id': new_app.id, 'message': 'Application created successfully'})
    except Exception as e:
        logger.error(f"Error in create_application: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/applications/<int:app_id>', methods=['PUT'])
def update_application(app_id):
    try:
        logger.debug(f"Updating application {app_id}")
        application = Application.query.get_or_404(app_id)
        data = request.json
        application.status = data.get('status', application.status)
        application.shutdown_verified = data.get('shutdown_verified', application.shutdown_verified)
        db.session.commit()
        logger.info(f"Application {app_id} updated successfully")
        return jsonify({'message': 'Application updated successfully'})
    except Exception as e:
        logger.error(f"Error in update_application: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers', methods=['GET'])
def get_servers():
    try:
        logger.debug("Fetching all servers")
        servers = Server.query.all()
        result = [server.to_dict() for server in servers]
        logger.debug(f"Found {len(result)} servers")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_servers: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/servers', methods=['POST'])
def create_server():
    try:
        data = request.json
        logger.debug(f"Creating new server with data: {data}")
        new_server = Server(
            hostname=data['hostname'],
            ip_address=data['ip_address'],
            app_id=data['app_id']
        )
        db.session.add(new_server)
        db.session.commit()
        logger.info(f"Server created successfully with id: {new_server.id}")
        return jsonify({'id': new_server.id, 'message': 'Server created successfully'})
    except Exception as e:
        logger.error(f"Error in create_server: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/applications/template', methods=['GET'])
def get_application_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['name', 'owner', 'web_ui', 'db_port'])
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=applications_template.csv'
    }

@app.route('/api/servers/template', methods=['GET'])
def get_server_template():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['hostname', 'ip_address', 'app_id'])
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=servers_template.csv'
    }

@app.route('/api/applications/import', methods=['POST'])
def import_applications():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400

        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        for row in csv_input:
            new_app = Application(
                name=row['name'],
                owner=row['owner'],
                web_ui=row.get('web_ui'),
                db_port=int(row['db_port']) if row.get('db_port') else None
            )
            db.session.add(new_app)
        
        db.session.commit()
        return jsonify({'message': 'Applications imported successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error importing applications: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/servers/import', methods=['POST'])
def import_servers():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400

        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        for row in csv_input:
            new_server = Server(
                hostname=row['hostname'],
                ip_address=row['ip_address'],
                app_id=int(row['app_id'])
            )
            db.session.add(new_server)
        
        db.session.commit()
        return jsonify({'message': 'Servers imported successfully'})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error importing servers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
