import re
from PyPDF2 import PdfReader
import spacy
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
# Chargement de la clé API Gemini
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialisation du modèle Gemini
model = genai.GenerativeModel("gemini-1.5-flash")

# Charge le modèle français
nlp = spacy.load("fr_core_news_sm")

# Ajout du sentencizer si le parser n'est pas dans la pipeline
if 'parser' not in nlp.pipe_names:
    nlp.add_pipe('sentencizer')

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extrait tout le texte d'un fichier PDF en concaténant toutes les pages.
    """
    with open(file_path, 'rb') as file:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()

import re

def extract_personal_info(text: str) -> dict:
    """
    Extrait prénom, nom et email depuis le texte brut.
    Gère les versions françaises et anglaises : Nom, Prénom, Name, First Name, Last Name.
    """
    lines = text.splitlines()
    nom, prenom, email = "", "", ""

    # Email : global match
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    if email_match:
        email = email_match.group(0)

    # Recherche ligne par ligne
    for line in lines:
        line_clean = line.strip()

        # Correspondance française
        nom_match_fr = re.match(r'Nom\s*[:=]\s*(.+)', line_clean, re.IGNORECASE)
        prenom_match_fr = re.match(r'Prénom\s*[:=]\s*(.+)', line_clean, re.IGNORECASE)

        # Correspondance anglaise
        first_name_match = re.match(r'(First\s*Name|Given\s*Name)\s*[:=]\s*(.+)', line_clean, re.IGNORECASE)
        last_name_match = re.match(r'(Last\s*Name|Surname|Family\s*Name|Name)\s*[:=]\s*(.+)', line_clean, re.IGNORECASE)

        if nom_match_fr:
            nom = nom_match_fr.group(1).strip()
        if prenom_match_fr:
            prenom = prenom_match_fr.group(1).strip()

        if last_name_match and not nom:
            nom = last_name_match.group(2).strip()
        if first_name_match and not prenom:
            prenom = first_name_match.group(2).strip()

    return {
        "first_name": prenom,
        "last_name": nom,
        "email": email
    }



import unicodedata
import re

def normalize_text(text):
    # Supprime les accents et met en minuscules
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    return text.lower()

def extract_education(text: str) -> list:
    """
    Extrait les blocs de texte liés à la formation académique de façon robuste.
    """
    normalized_text = normalize_text(text)
    lines = text.splitlines()
    education_blocks = []
    capture = False
    block = []

    # Liste de mots-clés éducation (sans accent)
    keywords = ["formation", "diplome", "etudes", "education", "degree", "academic background"]

    for idx, line in enumerate(lines):
        normalized_line = normalize_text(line)

        # Début d'une section formation ?
        if any(kw in normalized_line for kw in keywords):
            capture = True
            block = [line]
            continue

        if capture:
            if line.strip() == "" or re.match(r"^[A-Z\s]{5,}$", line):  # Section suivante détectée
                education_blocks.append("\n".join(block))
                capture = False
                block = []
            else:
                block.append(line)

    # Ajoute le dernier bloc si on arrive à la fin
    if capture and block:
        education_blocks.append("\n".join(block))

    return education_blocks

def parse_education_block_with_gemini(edu_block: str) -> dict:
    """
    Envoie un bloc de formation à Gemini pour extraire degree, institution, etc.
    """
    prompt = f"""
    Tu es un assistant intelligent. À partir du bloc suivant, structure les informations de formation en format JSON avec les champs :
    - degree (ex: Master, PhD)
    - specialty (ex: Informatique, Biologie)
    - institution (nom de l'université)
    - year (année ou période)
    - level (niveau académique ex: Licence, Master, Doctorat)

    Si une information est absente, mets null.

    Bloc de formation :
    \"\"\"{edu_block}\"\"\"
    """

    try:
        response = model.generate_content(prompt)
        cleaned = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned)
    except Exception as e:
        print(f"[ERREUR Gemini] {e}")
        return {
            "degree": None,
            "specialty": None,
            "institution": None,
            "year": None,
            "level": None
        }

