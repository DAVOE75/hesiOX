import spacy
from flask import Blueprint, request, jsonify

print('[spaCy API] Módulo spacy_api_test.py importado')
spacy_bp = Blueprint('spacy', __name__)

# Cargar modelo español solo una vez
nlp = spacy.load('es_core_news_md')

@spacy_bp.route('/api/spacy/clean2', methods=['POST'])
def spacy_clean():
    print("[spaCy API] Headers:", dict(request.headers))
    print("[spaCy API] Data raw:", request.data)
    print("[spaCy API] Is JSON:", request.is_json)
    data = request.get_json()
    print("[spaCy API] DATA RECIBIDA:", data)
    text = data.get('text', '') if data else ''
    if not text or not text.strip():
        print("[spaCy API] ERROR: No text provided")
        return jsonify({'error': 'No text provided'}), 400
    doc = nlp(text)
    # Texto limpio: solo frases bien segmentadas, sin espacios extra
    clean_text = ' '.join([sent.text.strip() for sent in doc.sents if sent.text.strip()])
    print("[spaCy API] TEXTO LIMPIO:", clean_text[:200], '...')
    return jsonify({'clean_text': clean_text})
