from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.sql import func
from src.database.session import Base

class DocumentProcess(Base):
    __tablename__ = "document_processes"

    id = Column(Integer, primary_key=True, index=True)
    gate_pass_no = Column(String, index=True)
    container_no = Column(String, index=True)
    status = Column(String, default="PENDING")
    
    # Store all the extracted metadata and fallback info
    extracted_data = Column(JSON) 
    
    # Store validation paths/warnings
    validation_status = Column(JSON)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
