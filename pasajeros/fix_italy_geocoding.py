import psycopg2
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import sys

def fix_italy_geocoding():
    try:
        conn = psycopg2.connect("dbname=hesiox user=hesiox_user password=garciap1975 host=localhost")
        cur = conn.cursor()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return

    # 1. Identify passengers in the Rome cluster (approx 244 people)
    # We use the bounding box confirmed earlier: lat 41.8-42.0, lon 12.4-12.6
    print("Finding passengers in Rome cluster...")
    cur.execute("""
        SELECT id, municipio, provincia, pais 
        FROM pasajeros_sirio 
        WHERE lat BETWEEN 41.8 AND 42.0 AND lon BETWEEN 12.4 AND 12.6;
    """)
    pasajeros = cur.fetchall()
    print(f"Found {len(pasajeros)} passengers in the Rome cluster.")

    geolocator = Nominatim(user_agent="hesiox_italy_fixer")
    
    fixed_count = 0
    cleared_count = 0
    failed_count = 0
    skipped_count = 0

    for pid, mun, prov, pais in pasajeros:
        # If it's a genuine Rome resident, skip it
        if mun and mun.lower().strip() in ['roma', 'rome']:
            print(f"Skipping genuine Rome resident ID {pid}")
            skipped_count += 1
            continue

        if not mun:
            # No municipality, clear coordinates as per plan to avoid false clusters
            print(f"ID {pid}: No municipality, clearing coordinates.")
            cur.execute("UPDATE pasajeros_sirio SET lat = NULL, lon = NULL WHERE id = %s;", (pid,))
            cleared_count += 1
            continue

        # Try to geocode
        search_query = f"{mun}, {prov or ''}, Italia".strip(", ")
        print(f"ID {pid}: Geocoding '{search_query}'...")
        
        try:
            location = geolocator.geocode(search_query, timeout=10)
            if location:
                # Basic check to ensure it's in Italy (lat between 35 and 48, lon between 6 and 19)
                if 35 < location.latitude < 48 and 6 < location.longitude < 19:
                    print(f"  Result: {location.latitude}, {location.longitude} ({location.address})")
                    cur.execute("UPDATE pasajeros_sirio SET lat = %s, lon = %s WHERE id = %s;", 
                                (location.latitude, location.longitude, pid))
                    fixed_count += 1
                else:
                    print(f"  Result outside Italy: {location.latitude}, {location.longitude}. Clearing.")
                    cur.execute("UPDATE pasajeros_sirio SET lat = NULL, lon = NULL WHERE id = %s;", (pid,))
                    cleared_count += 1
            else:
                print(f"  Not found. Clearing coordinates.")
                cur.execute("UPDATE pasajeros_sirio SET lat = NULL, lon = NULL WHERE id = %s;", (pid,))
                cleared_count += 1
        except GeocoderTimedOut:
            print(f"  Timeout for {search_query}. Skipping for now.")
            failed_count += 1
        except Exception as e:
            print(f"  Error: {e}")
            failed_count += 1
        
        # Commit every 10 records
        if (fixed_count + cleared_count) % 10 == 0:
            conn.commit()
            
        time.sleep(1) # Respect Nominatim usage policy

    conn.commit()
    cur.close()
    conn.close()

    print("\nProcessing finished:")
    print(f"  - Re-geocoded correctly: {fixed_count}")
    print(f"  - Coordinates cleared (missing or not found): {cleared_count}")
    print(f"  - Skipped (genuine Rome): {skipped_count}")
    print(f"  - Failed (timeouts/errors): {failed_count}")

if __name__ == "__main__":
    fix_italy_geocoding()
