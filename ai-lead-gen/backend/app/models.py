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
    plan = Column(String, default="free")          # free | growth | agency
    instagram_handle = Column(String)   # coach's own @handle (without @)
    tiktok_handle = Column(String)
    twitter_handle = Column(String)
    reddit_handle = Column(String)
    facebook_url = Column(String)
    linkedin_url = Column(String)
    offer_price = Column(Float, nullable=True)
    icp_pain_points = Column(Text, nullable=True)   # JSON array: pains the coach's ICP expresses
    onboarded = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Social proof testimonials: JSON list of {name, situation, result}
    testimonials = Column(Text, nullable=True)

    # Email verification
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String, nullable=True)

    # Trial
    trial_end_date = Column(DateTime, nullable=True)   # signup + 14 days; None = no trial

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
    profile_pic_url = Column(String)    # cached avatar URL from IG/TT

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
    # Intelligence fields (v5) — aspiration gap, price, trust, voice
    aspiration_gap_score = Column(Float, default=0.0)  # 0-100 gap between dreams and reality
    price_tier = Column(String, default="mid")          # premium | mid | budget
    trust_velocity = Column(String, default="unknown")  # fast | slow | unknown
    voice_tone_intensity = Column(Float, default=0.0)   # 0-100 emotional intensity score
    # Intelligence fields (v6) — churn prevention, emotional trajectory
    churn_risk = Column(Float, default=0.0)             # 0-1 risk of going cold
    emotion_history = Column(Text)                      # JSON: [{ts, emotion, score}]
    reengagement_message = Column(Text)                 # AI-generated re-engagement DM
    # Intelligence fields (v7) — CRM enrichment, attribution, sales
    enriched_data = Column(Text)                        # JSON: linkedin_role, income, tech_stack, etc.
    enriched_at = Column(DateTime)
    sales_script = Column(Text)                         # JSON: {opener, objections, closing, followup}
    nurture_sequence = Column(Text)                     # JSON: [{message, trigger, day}]
    nurture_step = Column(Integer, default=0)           # current nurture step
    converting_angle = Column(String)                   # angle that got the reply
    predicted_close_date = Column(DateTime)             # predicted close based on velocity

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    coach = relationship("Coach", back_populates="leads")


class LeadMagnet(Base):
    """A piece of content the coach gives away to attract leads."""
    __tablename__ = "lead_magnets"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    type = Column(String, default="pdf")   # pdf|video|ebook|call|course|other
    link = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    coach = relationship("Coach")


class KeywordTrigger(Base):
    """Comment keyword → auto-DM workflow."""
    __tablename__ = "keyword_triggers"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    keyword = Column(String, nullable=False)
    platform = Column(String, default="instagram")
    message_template = Column(Text)
    lead_magnet_id = Column(Integer, ForeignKey("lead_magnets.id"), nullable=True)
    trigger_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    coach = relationship("Coach")
    lead_magnet = relationship("LeadMagnet")


class AIConversation(Base):
    """AI clone conversation qualifying a lead."""
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    messages = Column(Text, default="[]")
    current_score = Column(Float, default=0.0)
    status = Column(String, default="active")  # active|hot|disqualified|handed_off
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead = relationship("Lead")
    coach = relationship("Coach")


class ContentAnalysis(Base):
    """Cached content intelligence analysis."""
    __tablename__ = "content_analyses"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    platform = Column(String)
    handle = Column(String)
    analysis_data = Column(Text)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    coach = relationship("Coach")


class CoachICP(Base):
    """Ideal Client Profile — generated by Claude, updated by learning from conversions."""
    __tablename__ = "coach_icp"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), unique=True, nullable=False)
    icp_data = Column(Text)           # Full JSON ICP document
    generated_at = Column(DateTime, default=datetime.utcnow)
    version = Column(Integer, default=1)

    coach = relationship("Coach", backref="icp")


class CompetitorIntelligence(Base):
    """Competitive intelligence scan results — auto-updated by scheduler."""
    __tablename__ = "competitor_intelligence"

    id = Column(Integer, primary_key=True, index=True)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    handle = Column(String, nullable=False)
    platform = Column(String)
    scan_data = Column(Text)          # JSON: content_themes, gaps, pricing, dissatisfied_count
    report_data = Column(Text)        # JSON: market_gaps, unique_angle, opportunities
    scanned_at = Column(DateTime, default=datetime.utcnow)

    coach = relationship("Coach")


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
