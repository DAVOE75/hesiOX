
import sqlite3
import re

db_path = "/opt/hesiox/noticias.db" # Standard path based on project structure

def clean_location_name(name):
    if not name: return ""
    prefijos = [
        r'^á\s+', r'^a\s+', r'^en\s+', r'^de\s+', r'^desde\s+', 
        r'^hasta\s+', r'^hacia\s+', r'^por\s+', r'^para\s+', r'^sobre\s+',
        r'^del\s+', r'^al\s+'
    ]
    cleaned = name.strip()
    for p in prefijos:
        cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE).strip()
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned

def run_cleanup():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Iniciando cleanup SQL...")
    
    # 1. Ciudad
    cursor.execute("SELECT id, name FROM ciudad")
    ciudades = cursor.fetchall()
    count_c = 0
    for id_c, name in ciudades:
        new_name = clean_location_name(name)
        if new_name != name:
            print(f"[CIUDAD] '{name}' -> '{new_name}'")
            try:
                cursor.execute("UPDATE ciudad SET name = ? WHERE id = ?", (new_name, id_c))
                count_c += 1
            except sqlite3.IntegrityError:
                print(f"  [!] Duplicado detectado: borrando '{name}'")
                cursor.execute("DELETE FROM ciudad WHERE id = ?", (id_c,))
    
    # 2. LugarNoticia
    cursor.execute("SELECT id, noticia_id, nombre, frecuencia FROM lugar_noticia")
    lugares = cursor.fetchall()
    count_l = 0
    for id_l, noticia_id, nombre, frecuencia in lugares:
        new_name = clean_location_name(nombre)
        if new_name != nombre:
            print(f"[LUGAR_NOTICIA] N:{noticia_id} '{nombre}' -> '{new_name}'")
            # Verificar si ya existe en la misma noticia
            cursor.execute("SELECT id, frecuencia FROM lugar_noticia WHERE noticia_id = ? AND nombre = ? AND id != ?", (noticia_id, new_name, id_l))
            existe = cursor.fetchone()
            if existe:
                id_existente, frec_existente = existe
                print(f"  [!] Fusionando frecuencia con registro {id_existente}")
                cursor.execute("UPDATE lugar_noticia SET frecuencia = ? WHERE id = ?", (frec_existente + frecuencia, id_existente))
                cursor.execute("DELETE FROM lugar_noticia WHERE id = ?", (id_l,))
            else:
                cursor.execute("UPDATE lugar_noticia SET nombre = ? WHERE id = ?", (new_name, id_l))
            count_l += 1
            
    conn.commit()
    conn.close()
    print(f"Finalizado. {count_c} ciudades y {count_l} lugares corregidos.")

if __name__ == "__main__":
    run_cleanup()
