import requests
import json
from typing import List, Dict, Tuple
from flask import current_app  # For Flask configuration access

class AcademicSearch:
    def __init__(self, api_key="aa2a5280646ebe83f26a7f57e4074147"):
        # API keys can be configured via Flask or passed directly
        self.api_key = api_key or current_app.config.get('SCOPUS_API_KEY', 'aa2a5280646ebe83f26a7f57e4074147')
        self.headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": self.api_key
        }
        self.base_orcid_url = "https://pub.orcid.org/v3.0"
        self.base_crossref = "https://api.crossref.org"
        self.base_google_scholar = "https://scholar.google.com/scholar"

    def get_orcid_id(self, family_name: str, given_name: str = "") -> List[Dict]:
        url = f"{self.base_orcid_url}/expanded-search/?q=family-name:{family_name}"
        if given_name:
            url += f"+AND+given-names:{given_name}"
        try:
            response = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
            return response.json().get('expanded-result', [])
        except Exception as e:
            print(f"Erreur ORCID: {str(e)}")
            return []

    def get_orcid_publications(self, orcid_id: str) -> List[Dict]:
        url = f"{self.base_orcid_url}/{orcid_id}/works"
        try:
            response = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
            works = response.json().get('group', [])
            return self._parse_orcid_works(works)
        except Exception as e:
            print(f"Erreur publications ORCID: {str(e)}")
            return []

    def _parse_orcid_works(self, works: List) -> List[Dict]:
        publications = []
        for work in works:
            try:
                w = work['work-summary'][0]
                pub = {
                    'title': w.get('title', {}).get('title', {}).get('value', ''),
                    'journal': w.get('journal-title', {}).get('value', ''),
                    'year': w.get('publication-date', {}).get('year', {}).get('value', ''),
                    'doi': self._extract_doi(w),
                    'citations': None,
                    'authors': self._extract_authors(w)
                }
                publications.append(pub)
            except Exception as e:
                print(f"Erreur parsing travail: {str(e)}")
        return publications

    def _extract_doi(self, work: Dict) -> str:
        for ext_id in work.get('external-ids', {}).get('external-id', []):
            if ext_id.get('external-id-type') == 'doi':
                return ext_id.get('external-id-value', '')
        return ''

    def _extract_authors(self, work: Dict) -> List[str]:
        return []

    def get_crossref_publications(self, author_name: str) -> List[Dict]:
        url = f"{self.base_crossref}/works?query.author={author_name}&rows=50"
        try:
            response = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
            items = response.json().get('message', {}).get('items', [])
            return self._parse_crossref_items(items)
        except Exception as e:
            print(f"Erreur Crossref: {str(e)}")
            return []

    def _parse_crossref_items(self, items: List) -> List[Dict]:
        publications = []
        for item in items:
            try:
                pub = {
                    'title': ' '.join(item.get('title', [''])),
                    'journal': item.get('container-title', [''])[0] if item.get('container-title') else '',
                    'year': item.get('created', {}).get('date-parts', [[None]])[0][0],
                    'doi': item.get('DOI', ''),
                    'citations': item.get('is-referenced-by-count', 0),
                    'authors': [a.get('given', '') + ' ' + a.get('family', '') for a in item.get('author', [])]
                }
                publications.append(pub)
            except Exception as e:
                print(f"Erreur parsing Crossref: {str(e)}")
        return publications

    def estimate_citations(self, title: str) -> int:
        try:
            params = {"q": title, "hl": "en", "as_sdt": "0,5"}
            response = requests.get(self.base_google_scholar, params=params, timeout=10)
            if "Cited by" in response.text:
                return int(response.text.split("Cited by")[1].split(">")[1].split("<")[0])
            return 0
        except Exception as e:
            print(f"Erreur estimation citations: {str(e)}")
            return 0

    def get_academic_data(self, full_name: str) -> Dict:
        family_name, given_name = self._split_name(full_name)
        orcid_profiles = self.get_orcid_id(family_name, given_name)
        orcid_publications = []

        if orcid_profiles:
            orcid_id = orcid_profiles[0]['orcid-id']
            orcid_publications = self.get_orcid_publications(orcid_id)

        crossref_publications = self.get_crossref_publications(full_name)
        all_publications = self._merge_publications(orcid_publications, crossref_publications)

        for pub in all_publications:
            if pub.get('citations') is None:
                pub['citations'] = self.estimate_citations(pub['title'])

        return {
            "orcid_id": orcid_profiles[0]['orcid-id'] if orcid_profiles else None,
            "publications": all_publications,
            "count": len(all_publications),
            "total_citations": sum(p.get('citations', 0) for p in all_publications)
        }

    def _split_name(self, full_name: str) -> Tuple[str, str]:
        parts = full_name.split()
        if len(parts) == 1:
            return (parts[0], "")
        return (" ".join(parts[:-1]), parts[-1])

    def _merge_publications(self, list1: List[Dict], list2: List[Dict]) -> List[Dict]:
        seen_dois = set()
        merged = []

        for pub in list1 + list2:
            doi = pub.get('doi')
            if doi and doi in seen_dois:
                continue
            if doi:
                seen_dois.add(doi)
            merged.append(pub)

        return merged
