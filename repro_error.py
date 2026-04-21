import os
from flask import Flask, render_template, url_for
from routes.noticias import noticias_bp

app = Flask(__name__, template_folder='templates')
app.secret_key = 'test'
app.register_blueprint(noticias_bp)

@app.route('/test_render')
def test_render():
    try:
        return render_template('mapa_corpus.html', publicaciones=[], csrf_token=lambda: 'mock_token')
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    with app.test_request_context():
        try:
            print(render_template('mapa_corpus.html', publicaciones=[], csrf_token=lambda: 'mock_token'))
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
