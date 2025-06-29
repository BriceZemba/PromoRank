from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class RecommendationEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
    
    def generate_recommendations(self, candidate, all_candidates) -> List[Dict]:
        """Génère des recommandations basées sur le profil"""
        recommendations = []
        
        # 1. Analyse des forces académiques
        academic_strength = self._evaluate_academic_strength(candidate)
        recommendations.append({
            'type': 'academic_strength',
            'content': f"Ce candidat montre une forte productivité académique avec {academic_strength['publications']} publications et un H-index de {academic_strength['h_index']}.",
            'score': academic_strength['score']
        })
        
        # 2. Comparaison avec les pairs
        peer_comparison = self._compare_with_peers(candidate, all_candidates)
        recommendations.append({
            'type': 'peer_comparison',
            'content': f"Le candidat se situe dans le top {peer_comparison['percentile']}% des candidats en termes d'impact scientifique.",
            'score': peer_comparison['score']
        })
        
        # 3. Adéquation avec les domaines de recherche
        domain_match = self._check_domain_match(candidate)
        recommendations.extend(domain_match)
        
        return sorted(recommendations, key=lambda x: x['score'], reverse=True)[:3]  # Top 3
    
    def _evaluate_academic_strength(self, candidate) -> Dict:
        """Évalue la force académique globale"""
        score = min(candidate.h_index * 2 + len(candidate.publications) * 0.1, 100)
        return {
            'publications': len(candidate.publications),
            'h_index': candidate.h_index,
            'score': score
        }
    
    def _compare_with_peers(self, candidate, all_candidates) -> Dict:
        """Compare le candidat avec les autres"""
        h_indices = [c.h_index for c in all_candidates]
        percentile = np.percentile(h_indices, candidate.h_index)
        score = min(percentile * 0.8, 100)
        return {
            'percentile': round(100 - percentile, 1),
            'score': score
        }
    
    def _check_domain_match(self, candidate) -> List[Dict]:
        """Vérifie l'adéquation avec les domaines clés"""
        # Implémentation basée sur l'analyse des publications
        domains = self._extract_research_domains(candidate)
        
        return [{
            'type': 'domain_match',
            'content': f"Expertise confirmée en {domain['name']} ({domain['strength']} publications).",
            'score': domain['strength'] * 5
        } for domain in domains]
    
    def _extract_research_domains(self, candidate) -> List[Dict]:
        """Extrait les domaines de recherche principaux"""
        # Analyse des titres et mots-clés des publications
        texts = [pub.title for pub in candidate.publications if pub.title]
        
        if not texts:
            return []
        
        # Utilisation de TF-IDF pour identifier les termes importants
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        feature_names = self.vectorizer.get_feature_names_out()
        
        # Agrégation des scores par terme
        total_tfidf = np.asarray(tfidf_matrix.sum(axis=0)).ravel()
        sorted_indices = total_tfidf.argsort()[::-1]
        
        # Mapping vers des domaines connus
        domain_mapping = {
            'intelligence': 'Intelligence Artificielle',
            'learning': 'Machine Learning',
            'network': 'Réseaux de Neurones',
            # ... autres mappings
        }
        
        domains = {}
        for idx in sorted_indices[:10]:  # Top 10 termes
            term = feature_names[idx]
            for key, domain in domain_mapping.items():
                if key in term:
                    domains[domain] = domains.get(domain, 0) + 1
        
        return [{'name': k, 'strength': v} for k, v in domains.items()]
    
def extract_specializations(publications):
    """Version alternative sans champ keywords"""
    from collections import defaultdict
    import re
    
    # Termes à exclure
    STOP_WORDS = {'study', 'research', 'effect', 'analysis', 'using', 'based'}
    
    specializations = defaultdict(int)
    
    for pub in publications:
        # Extraction depuis le titre
        if pub.title:
            words = re.findall(r'\b[a-z]{4,}\b', pub.title.lower())
            for word in words:
                if word not in STOP_WORDS:
                    specializations[word] += 1
        
        # Extraction depuis le journal (optionnel)
        if pub.journal:
            journal_keywords = re.split(r'[,&]|\bof\b', pub.journal.lower())
            for kw in journal_keywords:
                kw = kw.strip()
                if kw and 3 < len(kw) < 20:
                    specializations[kw] += 1
    
    # Mapping des termes techniques
    technical_terms = {
        'learning': 'Machine Learning',
        'network': 'Neural Networks',
        'quantum': 'Quantum Physics',
        # ... autres mappings
    }
    
    # Normalisation
    normalized = defaultdict(int)
    for term, count in specializations.items():
        normalized[technical_terms.get(term, term)] += count
    
    return sorted(normalized.items(), key=lambda x: x[1], reverse=True)[:3]

def calculate_candidate_score(candidate, h_index, target_specialization):
    """Calcule un score personnalisé"""
    score = h_index * 10  # Base score
    
    # Bonus pour spécialisation cible
    if target_specialization:
        for spec, count in candidate['specializations']:
            if target_specialization.lower() in spec.lower():
                score += count * 5
    
    # Bonus pour productivité
    score += len(candidate.publications) * 0.5
    
    return score