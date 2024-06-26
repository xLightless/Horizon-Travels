from flask import Flask, render_template
from flask_sitemap import Sitemap
from datetime import timedelta

sitemap = Sitemap()

def page_not_found(e):
    """ Returns Page not found if unavailable """
    return render_template('404.html'), 404

def create_flask_app():
    """ Creates a flask application """
    
    app = Flask(__name__, static_url_path='/static')
    app.secret_key = '192b9dec89xz1281has1jkl12jk12hb!][etr]#a1jhz38i0a08asdnas'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=86400)
    
    from .auth import auth
    from .views import views
    
    # Registers URL pointers
    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/auth')
    
    app.register_error_handler(404, page_not_found)
    
    # Initialises sitemap object
    sitemap.init_app(app)
    
    @app.route('/sitemap')
    def xml_sitemap():
        """ Generates a formatted sitemap """
        return sitemap.sitemap(), 200, {'Content-Type': 'text/xml', }
    
    return app
