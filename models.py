from sqlalchemy import Column, String, Text, BigInteger, TIMESTAMP, ForeignKey, PrimaryKeyConstraint, ForeignKeyConstraint
from sqlalchemy.sql import func
from database import Base

class Documents(Base):
    __tablename__ = "documents"

    record_id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )
    document_id = Column(String(500), nullable=False)
    intro = Column(Text)
    skills = Column(Text)
    chunks = Column(Text)



