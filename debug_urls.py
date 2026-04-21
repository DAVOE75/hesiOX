from app import app
from flask import url_for

with app.test_request_context():
    try:
        url_list = url_for('simulacion.list_routes')
        print(f"URL for 'simulacion.list_routes': {url_list}")
    except Exception as e:
        print(f"Error getting URL for 'simulacion.list_routes': {e}")

    try:
        url_analyze = url_for('simulacion.analyze_mc')
        print(f"URL for 'simulacion.analyze_mc': {url_analyze}")
    except Exception as e:
        print(f"Error getting URL for 'simulacion.analyze_mc': {e}")

    # Lista todos los endpoints del blueprint simulacion
    print("Endpoints in 'simulacion' blueprint:")
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('simulacion.'):
            print(f" - {rule.endpoint}: {rule}")
