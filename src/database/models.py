from sqlalchemy import Column, Integer, String, JSON, DateTime
from sqlalchemy.sql import func
from src.database.session import Base

class DocumentProcess(Base):
    __tablename__ = "document_processes"

    id = Column(String, primary_key=True, index=True)
    gate_pass_no = Column(String, index=True)
    container_no = Column(String, index=True)
    status = Column(String, default="PENDING")
    folder_path = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    
    # Store all the extracted metadata and fallback info
    extracted_data = Column(JSON, nullable=True) 
    
    # Store validation paths/warnings
    validation_status = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
