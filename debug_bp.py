try:
    from routes.simulacion import simulacion_bp
    print(f"Blueprint name: {simulacion_bp.name}")
    print(f"Blueprint prefix: {simulacion_bp.url_prefix}")
    print("Routes in blueprint:")
    for rule in simulacion_bp.deferred_functions:
        print(f" - {rule}")
except Exception as e:
    import traceback
    traceback.print_exc()
