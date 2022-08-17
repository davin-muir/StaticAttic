import os 
import pulumi.automation as auto
from flask import Flask, render_template



def ensure_plugins():
    ws = auto.LocalWorkspace()
    ws.install_plugin('aws', 'v4.0.0')

def create_app():
    ensure_plugins()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        #Configuration settings, similar to Django's settings.py file
        SECRET_KEY='belial',
        PROJECT_NAME='atstatic',
        PULUMI_ORG=os.environ.get('PULUMI_ORG'),
    )

    @app.route('/', methods=['GET'])
    def index():
        return render_template('index.html')


    #Registers both scripts as blueprints for the application.
    import sites 
    import virtual_machines
    app.register_blueprint(sites.bp)
    app.register_blueprint(virtual_machines.bp)

    return app

   

    

