from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from backend.db.base import Base

class MessageTemplate(Base):
    """
    ORM Model for localized message templates used by the AI and UI.
    Supports English, Hindi, Kannada, and Telugu.
    """
    __tablename__ = "message_templates"

    code = Column(String, primary_key=True, index=True) # e.g., 'advisor_check_sensor'
    en = Column(String, nullable=False)
    hi = Column(String, nullable=True)
    kn = Column(String, nullable=True)
    te = Column(String, nullable=True)
    ta = Column(String, nullable=True)
    mr = Column(String, nullable=True)

    def to_dict(self):
        return {
            "code": self.code,
            "en": self.en,
            "hi": self.hi,
            "kn": self.kn,
            "te": self.te
        }
