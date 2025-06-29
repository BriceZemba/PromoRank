from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import os
from .utils.evaluation import calculate_h_index
from app import db
from app.models import Candidate, Document, Publication, Recommendation
from app.utils.extraction import extract_text_from_pdf, extract_personal_info, extract_education, parse_education_block_with_gemini
from app.utils.scopus_api import  AcademicSearch
from app.utils.evaluation import rank_publications, calculate_candidate_score, calculate_originality_score, calculate_leadership_score, generate_evaluation_report, generate_pdf_report, generate_recommendation
from app.utils.recommendation_engine import RecommendationEngine, extract_specializations, calculate_candidate_score
from datetime import datetime
from config import Config
from flask import Blueprint, current_app  # Ajoutez current_app
from . import db  # Import relatif
from flask import jsonify

bp = Blueprint('main', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@bp.route('/')
def welcome():
    """Nouvelle page d'accueil avec choix de scénario"""
    return render_template('welcome.html')

@bp.route('/scenario_evaluation')
def scenario_evaluation():
    """Page d'évaluation pour les promotions"""
    # Logique d'évaluation existante à adapter
    return render_template('scenario_evaluation.html')

@bp.route('/upload', methods=['GET', 'POST'])
def upload():
    with current_app.app_context():
        candidates = Candidate.query.all()
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_folder = Config.UPLOAD_FOLDER
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            
            # Process the PDF
            text = extract_text_from_pdf(filepath)
            personal_info = extract_personal_info(text)
            # print(personal_info)
            # print(personal_info)
            education = parse_education_block_with_gemini(text)
            
            # Vérification si le candidat existe déjà
            existing_candidate = Candidate.query.filter_by(email=personal_info['email']).first()
            if existing_candidate:
            # Mise à jour du candidat existant
                candidate = existing_candidate
                flash('Ce candidat existe déjà, mise à jour des informations', 'info')
            else:
        
                # Create candidate record
                candidate = Candidate(
                    first_name=personal_info['first_name'],
                    last_name=personal_info['last_name'],
                    email=personal_info['email']
                )
                db.session.add(candidate)
                db.session.commit()
                
                # Create document record
                document = Document(
                    filename=filename,
                    filepath=filepath,
                    candidate_id=candidate.id,
                    extracted_data={
                        'education': education,
                        'raw_text': text[:1000] + "..."  # Store first 1000 chars
                    }
                )
                db.session.add(document)
                db.session.commit()
            
            # Récupère les publications avec l'alternative gratuite à Scopus
            academic_search = AcademicSearch()
            full_name = f"{candidate.first_name} {candidate.last_name}"
            academic_data = academic_search.get_academic_data(full_name)

            publications = []
            for pub in academic_data['publications']:
                publication = Publication(
                    title=pub.get('title', ''),
                    journal=pub.get('journal', ''),
                    year=int(pub.get('year', 0)) if pub.get('year') and str(pub.get('year')).isdigit() else None,
                    citations=pub.get('citations', 0),
                    scopus_id=pub.get('doi', ''),  # utilise le DOI comme identifiant unique ici
                    scopus_data=pub,               # stocke tout l'objet pour analyse ultérieure
                    candidate_id=candidate.id
                )
                db.session.add(publication)
                publications.append({
                    'title': publication.title,
                    'journal': publication.journal,
                    'year': publication.year,
                    'citations': publication.citations
                })

            db.session.commit()

            # Classement des publications
            ranked_publications = rank_publications(publications)

            
            return render_template('results.html', 
                                 candidate=candidate,
                                 publications=ranked_publications,
                                 education=education)
    
    return render_template('upload.html')

@bp.route('/candidates')
def list_candidates():
    # Récupère tous les candidats avec leurs publications
    candidates = Candidate.query.options(db.joinedload(Candidate.publications)).all()
    
    # Calcule les statistiques pour chaque candidat
    candidates_data = []
    for candidate in candidates:
        citations = [pub.citations or 0 for pub in candidate.publications]
        h_index = calculate_h_index(citations)
        
        candidates_data.append({
            'id': candidate.id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'email': candidate.email,
            'publication_count': len(candidate.publications),
            'total_citations': sum(citations),
            'h_index': h_index,
            'avg_citations': sum(citations) / len(citations) if citations else 0
        })
    
    # Trie par H-Index décroissant
    candidates_sorted = sorted(candidates_data, 
                             key=lambda x: x['h_index'], 
                             reverse=True)
    
    return render_template('candidates.html', candidates=candidates_sorted)

@bp.route('/candidate/<int:candidate_id>')

def candidate_detail(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    publications = Publication.query.filter_by(candidate_id=candidate_id)\
                                    .order_by(Publication.year.desc()).all()

    # Initialisation des données de citations par année
    citations_by_year = {}
    for pub in publications:
        year = pub.year
        citations = pub.citations or 0
        if year:
            citations_by_year[year] = citations_by_year.get(year, 0) + citations

    # Tri des années pour affichage
    years = sorted(citations_by_year.keys()) if citations_by_year else []
    citations_by_year_values = [citations_by_year[year] for year in years] if years else []

    # Liste des citations avec valeurs nulles traitées
    citations_list = [pub.citations or 0 for pub in publications]

    # Calcul du journal le plus fréquent
    if publications:
        journal_counts = {}
        for pub in publications:
            journal = pub.journal or "Inconnu"
            journal_counts[journal] = journal_counts.get(journal, 0) + 1
        top_journal = max(journal_counts, key=journal_counts.get)
    else:
        top_journal = "N/A"

    # Calcul des statistiques
    stats = {
        'total_publications': len(publications),
        'total_citations': sum(citations_list),
        'h_index': calculate_h_index(citations_list),
        'avg_citations': sum(citations_list) / len(publications) if publications else 0,
        'top_journal': top_journal,
        'years': years,
        'citations_by_year': citations_by_year_values
    }

    return render_template(
        'candidate_detail.html',
        candidate=candidate,
        publications=publications,
        stats=stats
    )

@bp.route('/instructions')
def instructions():
    """Page d'instructions pour l'utilisation de l'application"""
    steps = [
        {
            'number': 1,
            'title': "Téléversement du CV",
            'description': "Déposez un fichier PDF contenant le CV académique",
            'icon': "fa-upload"
        },
        {
            'number': 2,
            'title': "Extraction automatique",
            'description': "Le système extrait le nom, prénom et formations",
            'icon': "fa-robot"
        },
        {
            'number': 3,
            'title': "Recherche Scopus",
            'description': "Identification des publications via l'API Scopus",
            'icon': "fa-search"
        },
        {
            'number': 4,
            'title': "Analyse SFR",
            'description': "Calcul des scores et classement des publications",
            'icon': "fa-chart-line"
        },
        {
            'number': 5,
            'title': "Résultats",
            'description': "Visualisation interactive des résultats",
            'icon': "fa-file-alt"
        }
    ]
    
    scopus_info = {
        'coverage': "Plus de 25,000 revues académiques",
        'update_frequency': "Mise à jour quotidienne",
        'metrics': ["Citations", "SJR", "SNIP", "Score SFR"]
    }
    
    return render_template('instructions.html', 
                        steps=steps,
                        scopus_info=scopus_info)

@bp.route('/recommendations', methods=['GET', 'POST'])
def recommendations():
    if request.method == 'POST':
        num_candidates = int(request.form.get('num_candidates', 5))
        min_h_index = int(request.form.get('min_h_index', 0))
        specialization = request.form.get('specialization', '')
        
        # Récupération et tri des candidats
        candidates = Candidate.query.options(db.joinedload(Candidate.publications)).all()
        
        # Filtrage et classement
        filtered_candidates = []
        for candidate in candidates:
            citations = [pub.citations or 0 for pub in candidate.publications]
            h_index = calculate_h_index(citations)
            
            if h_index >= min_h_index:
                filtered_candidates.append({
                    'id': candidate.id,
                    'name': f"{candidate.first_name} {candidate.last_name}",
                    'h_index': h_index,
                    'specializations': extract_specializations(candidate.publications),
                    'score': calculate_candidate_score(candidate, h_index, specialization)
                })
        
        # Tri par score décroissant
        filtered_candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Sélection du top N
        selected_candidates = filtered_candidates[:num_candidates]
        
        return render_template('recommendations.html',
                            candidates=selected_candidates,
                            form_data=request.form)
    
    # GET request - afficher le formulaire
    return render_template('recommendations_form.html')


@bp.route('/evaluate_researcher', methods=['POST'])
def evaluate_researcher():

    academic_search = AcademicSearch()
    try:
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        criteria = request.form.getlist('criteria[]')

        if not first_name or not last_name:
            return jsonify({'error': "Nom et prénom requis"}), 400

        fullname = f"{first_name} {last_name}"
        academic_data = academic_search.get_academic_data(fullname)
        publications = academic_data['publications']

        # h-index estimé
        citations = sorted([p.get('citations', 0) for p in publications], reverse=True)
        h_index = sum(c >= i+1 for i, c in enumerate(citations))

        # Scores
        evaluation_results = {
            'impact_score': calculate_candidate_score(publications, h_index, "General Science") if 'impact' in criteria else None,
            'originality_score': calculate_originality_score(publications) if 'originality' in criteria else None
        }

        recommendation = generate_recommendation(evaluation_results)

        researcher_info = {
            'full_name': fullname,
            'h_index': h_index,
            'orcid_id': academic_data.get('orcid_id'),
            'total_publications': academic_data.get('count', 0)
        }

        pdf_filename = generate_pdf_report(researcher_info, evaluation_results, recommendation)
        pdf_url = url_for('static', filename=f'reports/{pdf_filename}', _external=True)

        return jsonify({
            'report': generate_evaluation_report(evaluation_results, criteria),
            'recommendation': recommendation,
            'researcher': researcher_info,
            'pdf_url': pdf_url
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
