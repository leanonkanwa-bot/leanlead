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
    offer_price = Column(Float, nullable=True)
    icp_pain_points = Column(Text, nullable=True)   # JSON array: pains the coach's ICP expresses
    onboarded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Social proof testimonials: JSON list of {name, situation, result}
    testimonials = Column(Text, nullable=True)

    # Autonomous agent settings
    agent_enabled = Column(Boolean, default=False)
    agent_frequency_hours = Column(Integer, default=6)
    agent_platforms = Column(Text)        # JSON array e.g. ["instagram","tiktok","linkedin"]
    agent_max_results_per_platform = Column(Integer, default=20)
    agent_dm_threshold = Column(Integer, default=70)
    agent_last_run_at = Column(DateTime)
    webhook_url = Column(String)
    competitor_accounts = Column(Text)    # JSON list of {url, platform, handle}

    leads = relationship("Lead", back_populates="coach", cascade="all, delete-orphan")
    prospecting_jobs = relationship("ProspectingJob", back_populates="coach", cascade="all, delete-orphan")
    agent_runs = relationship("AgentRun", back_populates="coach", cascade="all, delete-orphan")


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

    # Intelligence fields (v3)
    language = Column(String)                   # fr|en|es|pt|ar|other
    psychographic_profile = Column(Text)        # JSON: emotion, awareness_stage, style, language
    response_probability = Column(Float)        # 0-100 predicted reply rate
    dm_variant_b = Column(Text)                 # A/B test second variant
    dm_variant_sent = Column(String)            # "A" or "B"
    warming_status = Column(String, default="none")  # none|comment_ready|commented|dm_ready
    warming_comment = Column(Text)              # AI-generated comment to post before DM
    source_tag = Column(String)                 # viral_post|competitor_audience|direct|hashtag
    # Intelligence fields (v4)
    predicted_objection = Column(Text)          # #1 objection pre-empted in DM
    score_delta = Column(Float)                 # change in score since last rescan
    escalation_alert = Column(Boolean, default=False)  # True when pain is escalating

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


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)

    status = Column(String, default="running")  # running | done | error
    platforms_searched = Column(Text)           # JSON list
    leads_found = Column(Integer, default=0)
    leads_qualified = Column(Integer, default=0)
    dms_generated = Column(Integer, default=0)
    high_score_leads = Column(Integer, default=0)
    error_message = Column(Text)

    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)

    coach = relationship("Coach", back_populates="agent_runs")
