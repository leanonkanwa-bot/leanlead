from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class Coach(Base):
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    name = Column(String, nullable=False)
    niche = Column(String)
    offer_description = Column(Text)
    target_audience = Column(Text)
    calendly_link = Column(String)
    airtable_base_id = Column(String)
    airtable_api_key = Column(String)
    apify_api_key = Column(String)
    onboarded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    leads = relationship("Lead", back_populates="coach", cascade="all, delete-orphan")
    prospecting_jobs = relationship("ProspectingJob", back_populates="coach", cascade="all, delete-orphan")


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)

    # Profile
    name = Column(String)
    handle = Column(String)
    platform = Column(String, default="instagram")
    profile_url = Column(String)
    bio = Column(Text)
    followers = Column(Integer, default=0)
    posts_summary = Column(Text)

    # Qualification
    qualification_score = Column(Float, default=0.0)
    qualification_reason = Column(Text)
    pain_points = Column(Text)          # JSON array stored as string
    recommended_angle = Column(Text)

    # Kanban stage: new | contacted | replied | booked | closed
    stage = Column(String, default="new")

    # Outreach
    outreach_message = Column(Text)
    messaged_at = Column(DateTime)

    # Follow-ups (D+2, D+4, D+7)
    followup_d2_message = Column(Text)
    followup_d2_sent_at = Column(DateTime)
    followup_d4_message = Column(Text)
    followup_d4_sent_at = Column(DateTime)
    followup_d7_message = Column(Text)
    followup_d7_sent_at = Column(DateTime)

    # Reply handling
    reply_received = Column(Text)
    reply_received_at = Column(DateTime)
    suggested_reply = Column(Text)

    # CRM
    notes = Column(Text)
    airtable_record_id = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    coach = relationship("Coach", back_populates="leads")


class ProspectingJob(Base):
    __tablename__ = "prospecting_jobs"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)

    platform = Column(String)           # instagram | tiktok
    hashtags = Column(Text)             # JSON list
    max_results = Column(Integer, default=20)

    # Status: pending | running | done | error
    status = Column(String, default="pending")
    leads_found = Column(Integer, default=0)
    error_message = Column(Text)

    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)

    coach = relationship("Coach", back_populates="prospecting_jobs")
