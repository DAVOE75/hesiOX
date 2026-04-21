import psycopg2

def migrate():
    conn_str = "postgresql://hesiox_user:garciap1975@localhost/hesiox"
    new_columns = [
        "keelsons_connected_butts",
        "frames_riveted_rivets_size",
        "plating_garboard_riveting_to_keel",
        "plating_garboard_edges_riveting",
        "plating_bilge_butts_thickness",
        "plating_side_edges_riveting",
        "plating_side_butts_riveting",
        "plating_sheerstrake_edges",
        "plating_sheerstrake_butts",
        "plating_spar_sheerstrake_butts",
        "plating_stringer_plate_butts",
        "plating_spar_stringer_plate_butts",
        "plating_laps_breadth_double",
        "plating_laps_breadth_single",
        "butt_straps_riveted_type",
        "breasthooks_no",
        "crutches_no",
        "workmanship_plating_butts",
        "workmanship_carvel_edges",
        "workmanship_fillings_solid",
        "workmanship_riveting_holes",
        "workmanship_riveting_countersunk",
        "workmanship_rivets_break",
        "rigging_standing_running",
        "rigging_quality",
        "windlass_maker",
        "windlass_condition",
        "capstan_condition",
        "rudder_condition",
        "pumps_condition",
        "boats_long_boats_no",
        "boats_steam_launch_no",
        "engine_room_skylights_const",
        "engine_room_skylights_secured",
        "deadlights_bad_weather",
        "coal_bunker_openings_const",
        "coal_bunker_openings_lids",
        "coal_bunker_openings_height",
        "scuppers_arrangements",
        "cargo_hatchways_formed",
        "main_hatch_size",
        "fore_hatch_size",
        "quarter_hatch_size",
        "extraordinary_size_framed",
        "shifting_beams_arrangement",
        "hatches_strong_efficient",
        "iron_quality",
        "manufacturers_trade_mark",
        "builder_signature",
        "surveyor_signature"
    ]
    
    try:
        conn = psycopg2.connect(conn_str)
        conn.autocommit = True
        cur = conn.cursor()
        print("Connected to database.")
        
        for col in new_columns:
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='lloyds_register_survey_inspeccion_absoluta' AND column_name='{col}'")
            if not cur.fetchone():
                print(f"Adding column: {col}")
                cur.execute(f"ALTER TABLE lloyds_register_survey_inspeccion_absoluta ADD COLUMN {col} VARCHAR(255)")
            else:
                print(f"Column {col} already exists.")
        
        cur.close()
        conn.close()
        print("Migration completed!")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    migrate()
