import sys
import os

# Añadir el path del proyecto para importar db y app
sys.path.append('/opt/hesiox')
from app import app
from models import db, LloydsFicha

def populate_chronology():
    with app.app_context():
        ficha = LloydsFicha.query.first()
        if not ficha:
            ficha = LloydsFicha()
            db.session.add(ficha)
        
        # --- HEADER INFO ---
        ficha.special_survey_no = "1764 (Order for Special Survey)"
        ficha.special_survey_date = "14th June 1882"
        ficha.builders_yard_no = "385 (R. Napier & Sons Yard)"
        
        # --- 1st. Frame & Structure ---
        # 1882. June 5, 8, 14, 20. July 5, 11. Aug 1, 10, 18, 22, 29. Sept 8, 25. Oct 3, 10, 13, 18, 30.
        ficha.survey_1st_frame = "1882: June 5, 8, 14, 20; July 5, 11; Aug 1, 10, 18, 22, 29; Sept 8, 25; Oct 3, 10, 13, 18, 30. (Parts of the frame, when in place, and before plating was wrought)"

        # --- 2nd. Plating & Riveting ---
        # Nov 6, 8, 15, 17, 22, 27. Dec 5, 7, 11, 20, 21, 23, 29. 1883. Jan 8, 11, 15, 18, 22, 25, 31.
        ficha.survey_2nd_plating = "1882: Nov 6, 8, 15, 17, 22, 27; Dec 5, 7, 11, 20, 21, 23, 29. 1883: Jan 8, 11, 15, 18, 22, 25, 31. (On the plating during the process of riveting)"

        # --- 3rd. Beams & Fastenings ---
        # Feb 7, 10, 12, 13, 19, 23, 27. Mar 1, 5, 8, 13, 20, 27. Apr 4, 11, 16, 19, 23. 
        ficha.survey_3rd_beams = "1883: Feb 7, 10, 12, 13, 19, 23, 27; Mar 1, 5, 8, 13, 20, 27; Apr 4, 11, 16, 19, 23. (When the beams were in and fastened, and before the decks were laid)"

        # --- 4th. Complete Hull ---
        # May 2, 8, 10, 16, 22, 29, 30. June 4, 11, 12, 13, 16.
        ficha.survey_4th_complete = "1883: May 2, 8, 10, 16, 22, 29, 30; June 4, 11, 12, 13, 16. (When ship was complete, and before the plating was finally coated or cemented)"

        # --- 5th. Launched & Equipped ---
        ficha.survey_5th_launched = "June 16, 1883 (After the ship was launched and equipped)"
        
        db.session.commit()
        print("Chronology population complete!")

if __name__ == "__main__":
    populate_chronology()
