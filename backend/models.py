# models.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, func, Text
from db import Base


class MasterSpec(Base):
    """
    One row per (param, source, origin_filename / manual). This preserves all
    extracted values from multiple documents. A resolved 'master' is computed
    at runtime based on priority and uploaded_at.
    """
    __tablename__ = "master_specs"
    id = Column(Integer, primary_key=True, index=True)
    param = Column(String(255), nullable=False, index=True)   # not unique: multiple rows per param allowed
    value = Column(String(255))         # canonical numeric/text value (string)
    unit = Column(String(50))          # unit (mm, µm, bar, °C)
    raw = Column(Text)           # raw text we parsed - using Text for longer content
    source = Column(String(100))        # which source chosen: DOCX/PDF/Image/MANUAL
    origin = Column(String(255))        # original filename or identifier
    priority = Column(Integer, default=0)  # higher = more trusted / newer
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    meta = Column(JSON, nullable=True)     # optional: extra metadata


class RawExtraction(Base):
    __tablename__ = "raw_extractions"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(255))
    origin = Column(String(255))
    raw_text = Column(Text)  # Using Text for potentially long content
    meta_info = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
