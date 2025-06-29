from datetime import datetime
from app import db
from . import db  # Import relatif

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    documents = db.relationship('Document', backref='candidate', lazy=True, cascade="all, delete-orphan")
    publications = db.relationship('Publication', backref='candidate', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Candidate {self.first_name} {self.last_name}>'
    
class Publication(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(500), nullable=False)
        #keywords = db.Column(db.String(500))
        journal = db.Column(db.String(300))
        year = db.Column(db.Integer)
        citations = db.Column(db.Integer, default=0)
        scopus_id = db.Column(db.String(100))
        scopus_data = db.Column(db.JSON)
        sfr_score = db.Column(db.Float)
        rank = db.Column(db.Integer)
        candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)

def __repr__(self):
    return f'<Publication {self.title[:50]}>'

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    extracted_data = db.Column(db.JSON)

class Recommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    recommendation_type = db.Column(db.String(50), nullable=False)  # 'recruitment', 'promotion', 'funding'
    content = db.Column(db.Text, nullable=False)
    score = db.Column(db.Float, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    candidate = db.relationship('Candidate', backref='recommendations')
