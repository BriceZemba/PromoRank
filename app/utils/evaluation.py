from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
from datetime import datetime

def calculate_sfr_score(publication):
    """Calculate Scientific Field Rank (SFR) score based on publication metrics"""
    citations = publication.get('citations', 0)
    journal_impact = publication.get('journal_impact', 1)
    year = publication.get('year', datetime.now().year)
    
    # Normalize citations by publication age (simplified approach)
    age = datetime.now().year - year
    normalized_citations = citations / (age + 1)
    
    # Calculate SFR score
    sfr_score = normalized_citations * journal_impact
    
    return sfr_score

def calculate_h_index(citations):
    """Calcule l'h-index en gérant les valeurs nulles"""
    citations = sorted((c for c in citations if c is not None), reverse=True)
    h = 0
    for i, c in enumerate(citations):
        if c >= i + 1:
            h = i + 1
    return h

def rank_publications(publications):
    """Rank publications by SFR score"""
    for pub in publications:
        pub['sfr_score'] = calculate_sfr_score(pub)
    
    # Sort by SFR score descending
    sorted_pubs = sorted(publications, key=lambda x: x['sfr_score'], reverse=True)
    
    # Add rank
    for i, pub in enumerate(sorted_pubs):
        pub['rank'] = i + 1
    
    return sorted_pubs

def calculate_candidate_score(publications):
    """Score d'impact basé sur le nombre total de citations"""
    total_citations = sum(pub.get('citations', 0) for pub in publications)
    return min(total_citations / 10, 100)

def calculate_originality_score(publications):
    """Originalité estimée par la diversité des domaines ou types de publication"""
    topics = set(pub.get('field') for pub in publications if pub.get('field'))
    return min(len(topics) * 10, 100)

def calculate_leadership_score(publications):
    """Leadership basé sur le nombre de fois où le chercheur est 1er ou dernier auteur"""
    leadership_count = sum(
        1 for pub in publications
        if pub.get('author_position') in ['first', 'last']
    )
    return min(leadership_count * 10, 100)

def generate_evaluation_report(results, criteria):
    """Génère un résumé des scores"""
    report = "### Résumé de l'évaluation\n"

    if 'impact' in criteria:
        impact_score = results.get('impact_score')
        if impact_score is not None:
            report += f"- Impact scientifique : {impact_score:.2f}/100\n"
        else:
            report += "- Impact scientifique : Donnée non disponible\n"

    if 'originality' in criteria:
        originality_score = results.get('originality_score')
        if originality_score is not None:
            report += f"- Originalité : {originality_score:.2f}/100\n"
        else:
            report += "- Originalité : Donnée non disponible\n"

    if 'leadership' in criteria:
        leadership_score = results.get('leadership_score')
        if leadership_score is not None:
            report += f"- Leadership : {leadership_score:.2f}/100\n"
        else:
            report += "- Leadership : Donnée non disponible\n"

    return report



def generate_pdf_report(researcher_info, evaluation_results, recommendation, path="static/reports"):
    if not os.path.exists(path):
        os.makedirs(path)

    filename = f"{researcher_info['full_name'].replace(' ', '_')}_evaluation_report.pdf"
    filepath = os.path.join(path, filename)

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Rapport d'Évaluation Scientifique")

    y -= 40
    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Nom complet : {researcher_info['full_name']}")
    y -= 20
    c.drawString(50, y, f"ORCID : {researcher_info.get('orcid_id', 'Non disponible')}")
    y -= 20
    c.drawString(50, y, f"Nombre de publications : {researcher_info['total_publications']}")
    y -= 20
    c.drawString(50, y, f"h-index estimé : {researcher_info['h_index']}")

    y -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Scores d'évaluation :")

    y -= 20
    for key, score in evaluation_results.items():
        if score is not None:
            label = key.replace('_score', '').capitalize()
            c.drawString(70, y, f"- {label} : {score:.2f}/100")
            y -= 20

    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Recommandation finale :")
    y -= 20
    c.setFont("Helvetica", 12)
    c.drawString(70, y, recommendation)

    y -= 40
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, y, f"Document généré le {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    c.save()
    return filename  # pour le lien de téléchargement

def generate_recommendation(results: dict) -> str:
    """
    Génère une recommandation à partir des scores d'évaluation.
    - Moyenne >= 75 → ✅ Recommandation forte
    - Moyenne 50–74 → ⚠️ Recommandation avec réserve
    - Moyenne < 50 → ❌ Non recommandé
    """
    scores = [score for score in results.values() if score is not None]

    if not scores:
        return "⚠️ Aucune donnée suffisante pour une évaluation complète."

    average = sum(scores) / len(scores)

    if average >= 75:
        return "✅ Recommandation : Promotion fortement recommandée."
    elif average >= 50:
        return "⚠️ Recommandation : Promotion envisageable avec réserve."
    else:
        return "❌ Recommandation : Ne pas recommander la promotion."


