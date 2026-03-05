from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, index=True) # Celery task ID
    company_id = Column(Integer, ForeignKey("companies.id"))
    status = Column(String, default="pending")
    result_data = Column(JSON, nullable=True) # The final insights
    email = Column(String, nullable=True)      # Optional: notify user when done
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    company = relationship("Company")
