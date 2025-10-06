# models.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, func
from db import Base


class MasterSpec(Base):
    """
    One row per (param, source, origin_filename / manual). This preserves all
    extracted values from multiple documents. A resolved 'master' is computed
    at runtime based on priority and uploaded_at.
    """
    __tablename__ = "master_specs"
    id = Column(Integer, primary_key=True, index=True)
    param = Column(String, nullable=False, index=True)   # not unique: multiple rows per param allowed
    value = Column(String)         # canonical numeric/text value (string)
    unit = Column(String)          # unit (mm, µm, bar, °C)
    raw = Column(String)           # raw text we parsed
    source = Column(String)        # which source chosen: DOCX/PDF/Image/MANUAL
    origin = Column(String)        # original filename or identifier
    priority = Column(Integer, default=0)  # higher = more trusted / newer
    uploaded_at = Column(DateTime, server_default=func.now())
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    meta = Column(JSON, nullable=True)     # optional: extra metadata


class RawExtraction(Base):
    __tablename__ = "raw_extractions"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String)
    origin = Column(String)
    raw_text = Column(String)
    meta_info = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
