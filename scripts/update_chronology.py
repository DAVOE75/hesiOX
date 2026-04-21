import psycopg2

DB_URL = "postgresql://hesiox_user:garciap1975@localhost/hesiox"

def update_chronology():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        # Construction dates provided by user
        chronology_text = """CRONOLOGÍA DE CONSTRUCCIÓN:
- Contrato: 1883-01-01
- Puesta de Quilla: 1883-02-15
- Estructura (Cuadernas): 1883-05-10
- Planchaje y Remachado: 1883-08-20
- Botadura: 1883-11-25
- Instalación de Motores: 1884-01-15
- Pruebas de Mar: 1884-03-30
- Entrega Final: 1884-04-12"""

        updates = {
            'special_survey_date': '1883-01-01 (Contrato)',
            'survey_1st_frame': '1883-05-10 (Cuadernas)',
            'survey_2nd_plating': '1883-08-20 (Planchaje)',
            'survey_5th_launched': '1883-11-25 (Botadura)',
            'general_remarks_observaciones_generales': chronology_text
        }

        # Update record ID 1
        for col, val in updates.items():
            cur.execute(f"UPDATE lloyds_register_survey_inspeccion_absoluta SET {col} = %s WHERE id = 1", (val,))

        conn.commit()
        print("Chronology updated successfully.")
        cur.close()
        conn.close()

    except Exception as ex:
        print(f"Error: {ex}")

if __name__ == "__main__":
    update_chronology()
