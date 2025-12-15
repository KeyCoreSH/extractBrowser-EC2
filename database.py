from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))

class ExtractionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.String(50))
    
    # S3 Links
    s3_original_key = db.Column(db.String(255))
    s3_preview_key = db.Column(db.String(255))
    s3_original_url = db.Column(db.String(500))
    s3_preview_url = db.Column(db.String(500))
    
    # AI Stats
    model_name = db.Column(db.String(50))
    input_tokens = db.Column(db.Integer, default=0)
    output_tokens = db.Column(db.Integer, default=0)
    total_tokens = db.Column(db.Integer, default=0)
    total_tokens = db.Column(db.Integer, default=0)
    confidence = db.Column(db.Float, default=0.0)
    
    # Data
    structured_data = db.Column(db.Text)  # JSON stringified
    
    # Meta
    processing_time_ms = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='success') # success, error
    error_message = db.Column(db.Text)
    
    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'document_type': self.document_type,
            's3_original_url': self.s3_original_url,
            's3_preview_url': self.s3_preview_url,
            'tokens': {
                'input': self.input_tokens,
                'output': self.output_tokens,
                'total': self.total_tokens
            },
            'confidence': self.confidence,
            'processing_time_ms': self.processing_time_ms,
            'created_at': self.created_at.isoformat(),
            'status': self.status
        }
