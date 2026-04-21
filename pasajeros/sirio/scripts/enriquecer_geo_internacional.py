import os
from sqlalchemy import create_engine, text

# Conexión a la base de datos
DATABASE_URL = "postgresql+psycopg2://hesiox_user:garciap1975@localhost/hesiox"
engine = create_engine(DATABASE_URL)

def run_update():
    with engine.begin() as conn:
        # 1. Correcciones de PAÍS erróneo (basado en municipio)
        print("Corrigiendo países mal asignados...")
        # Ferraras y otros italianos en el limbo
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Italia', region = 'Emilia-Romaña', provincia = 'Ferrara' 
            WHERE municipio ILIKE '%Ferrara%' AND (pais IN ('Estados Unidos', 'Austria', 'Alemania') OR pais IS NULL);
        """))
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Italia', region = 'Véneto', provincia = 'Verona', municipio = 'San Bonifacio' 
            WHERE municipio ILIKE '%San Bonifacio%';
        """))
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Italia', region = 'Calabria', provincia = 'Cosenza', municipio = 'Rossano' 
            WHERE municipio ILIKE '%Rossano%';
        """))
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Italia', region = 'Calabria', provincia = 'Cosenza', municipio = 'Paula' 
            WHERE municipio ILIKE '%Paula%' AND pais = 'Turquía';
        """))
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Italia', region = 'Marcas', provincia = 'Macerata', municipio = 'Monte San Giusto' 
            WHERE municipio ILIKE '%Monte San Giusto%';
        """))
        
        # Reino Unido (y caso específico Vonier)
        print("Enriqueciendo Reino Unido (Buckfastleigh)...")
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Reino Unido', region = 'England', provincia = 'Devon', municipio = 'Buckfastleigh' 
            WHERE municipio ILIKE '%Buckfastleigh%' OR apellidos ILIKE '%VONIER%';
        """))

        # 2. Enriquecimiento Líbano / Siria / Turquía
        print("Enriqueciendo Líbano, Siria y Turquía...")
        # Directriz del usuario: Turquía -> Ankara
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Turquía', region = 'Ankara', provincia = 'Ankara', municipio = 'Ankara' 
            WHERE (pais = 'Turquía' OR pais = 'Imperio Otomano') AND (municipio IS NULL OR municipio = '' OR municipio = 'Ankara');
        """))
        
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Líbano', region = 'Beirut', provincia = 'Beirut' 
            WHERE municipio ILIKE '%Beirut%';
        """))
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Líbano', region = 'Mont-Liban', provincia = 'Baabda' 
            WHERE municipio ILIKE '%Montelíbano%' OR municipio ILIKE '%Mount Lebanon%';
        """))

        # 3. Enriquecimiento Argentina / Uruguay / Brasil
        print("Enriqueciendo América del Sur...")
        # ARGENTINA: Provincia (GADM Level 1) -> region, Departamento (GADM Level 2) -> provincia
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Argentina', region = 'Santa Fe', provincia = 'Las Colonias' 
            WHERE (municipio ILIKE '%Las Colonias%' OR provincia ILIKE '%Santa Fe%') AND (pais = 'Argentina' OR pais IS NULL);
        """))
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Argentina', region = 'Buenos Aires', provincia = 'Buenos Aires' 
            WHERE municipio ILIKE '%Buenos Aires%' AND (pais = 'Argentina' OR pais IS NULL);
        """))
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Uruguay', region = 'Montevideo', provincia = 'Montevideo' 
            WHERE municipio ILIKE '%Montevideo%' AND (pais = 'Uruguay' OR pais IS NULL);
        """))
        
        # 4. Normalización de REGIONES para GADM
        print("Normalizando nombres de regiones y provincias...")
        conn.execute(text("UPDATE pasajeros_sirio SET region = 'Santa Fe' WHERE region ILIKE '%Santa Fe%';"))
        conn.execute(text("UPDATE pasajeros_sirio SET region = 'São Paulo' WHERE region ILIKE '%Sao Paulo%';"))
        conn.execute(text("UPDATE pasajeros_sirio SET region = 'Montenegro' WHERE pais = 'Montenegro';"))

        # 5. Lógica para países históricos (Austro-Hungría)
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Austria', region = 'Steiermark', provincia = 'Graz' 
            WHERE municipio ILIKE '%Graz%';
        """))
        conn.execute(text("""
            UPDATE pasajeros_sirio 
            SET pais = 'Croacia', region = 'Karlovačka', provincia = 'Ogulin' 
            WHERE municipio ILIKE '%Ogulin%';
        """))

if __name__ == "__main__":
    run_update()
    print("✅ Enriquecimiento geográfico completado.")
