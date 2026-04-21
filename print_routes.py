import os
import sys

# Change to the application directory
sys.path.append('/opt/hesiox')
os.chdir('/opt/hesiox')

try:
    from app import app
    with app.app_context():
        print("---- REGISTERED ROUTES ----")
        for rule in app.url_map.iter_rules():
            if 'weather' in str(rule) or 'espacial' in str(rule):
                print(f"{rule.methods} {rule}")
        print("---------------------------")
except Exception as e:
    import traceback
    traceback.print_exc()
