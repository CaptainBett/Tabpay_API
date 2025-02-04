from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Float, Enum, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from datetime import datetime

# Base class for all models
from .utils import Base


class RoleType(PyEnum):
    CHAIRMAN = "chairman"
    SECRETARY = "secretary"
    TREASURER = "treasurer"

class UserRole(PyEnum):
    SUPERUSER = "superuser"
    ADMIN = "admin"

# -------------------
# User Models
# -------------------
class User(Base):
    """
    A User is an account that can log in. (For example, an admin registers and then, after approval, 
    logs in to manage his/her umbrella.)
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String, unique=True, index=True)
    password = Column(String)
    is_active = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    role = Column(Enum(UserRole))  # SUPERUSER or ADMIN
    registered_at = Column(DateTime, default=datetime.now())
    
    # Relationships
    umbrella = relationship("Umbrella", back_populates="admin", uselist=False)

class Umbrella(Base):
    """
    An umbrella is the top‐level grouping in TabPay. An admin creates an umbrella,which contains blocks
    """
    __tablename__ = "umbrellas"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    location = Column(String)
    created_at = Column(DateTime, default=datetime.now())
    
    # Foreign Keys
    admin_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    admin = relationship("User", back_populates="umbrella")
    blocks = relationship("Block", back_populates="umbrella")

# -------------------
# Organizational Structure
# -------------------
class Block(Base):
    """
    A Block belongs to an umbrella and groups one or more zones.
    """
    __tablename__ = "blocks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.now())
    
    # Foreign Keys
    parent_umbrella_id = Column(Integer, ForeignKey("umbrellas.id"))
    
    # Relationships
    umbrella = relationship("Umbrella", back_populates="blocks")
    zones = relationship("Zone", back_populates="parent_block")
    meetings = relationship("Meeting", back_populates="block")
    roles = relationship("BlockRole", back_populates="block")

class Zone(Base):
    """
    Zones are subdivisions of a block. Members are added to zones.
    """
    __tablename__ = "zones"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.now())

    
    # Foreign Keys
    parent_block_id = Column(Integer, ForeignKey("blocks.id"))
    
    # Relationships
    parent_block = relationship("Block", back_populates="zones")
    members = relationship("MemberBlockAssociation", back_populates="zone")

# -------------------
# Member Management
# -------------------
class Member(Base):
    """
    A Member is a person (outside of the authentication system) who belongs to zones.
    """
    __tablename__ = "members"
    
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    image_file = Column(String(50))
    registered_at = Column(DateTime, default=datetime.now())
    
    # Relationships
    block_associations = relationship("MemberBlockAssociation", back_populates="member")
    contributions = relationship("Contribution", back_populates="member")
    
    # These properties pull data from the first associated MemberBlockAssociation.
    @property
    def phone_number(self) -> str:
        if self.block_associations:
            return self.block_associations[0].phone_number
        return ""  # or None, depending on your design

    @property
    def id_number(self) -> str:
        if self.block_associations:
            return self.block_associations[0].id_number
        return ""
    
    @property
    def acc_number(self) -> str:
        if self.block_associations:
            return self.block_associations[0].acc_number
        return ""


class MemberBlockAssociation(Base):
    """
    This association object links a Member to a Zone.
    (Since zones belong to blocks, this implicitly associates the member with a block.) We also store fields that must be unique at the block level.
    """
    __tablename__ = "member_block_associations"
    
    id = Column(Integer, primary_key=True)
    
    # Foreign Keys
    member_id = Column(Integer, ForeignKey("members.id"))
    block_id = Column(Integer, ForeignKey("blocks.id"))
    zone_id = Column(Integer, ForeignKey("zones.id"))
    
    # Unique member details per block
    phone_number = Column(String, index=True)
    id_number = Column(String, index=True)
    acc_number = Column(String, index=True)
    
    # Relationships
    member = relationship("Member", back_populates="block_associations")
    block = relationship("Block")
    zone = relationship("Zone", back_populates="members")
    
    # Unique constraints
    __table_args__ = (
        UniqueConstraint('member_id', 'block_id', name='_member_block_uc'),
        UniqueConstraint('block_id', 'phone_number', name='_block_phone_uc'),
        UniqueConstraint('block_id', 'id_number', name='_block_id_uc'),
        UniqueConstraint('block_id', 'acc_number', name='_block_acc_uc'),
    )

# -------------------
# Roles & Permissions
# -------------------
class BlockRole(Base):
    __tablename__ = "block_roles"
    
    id = Column(Integer, primary_key=True)
    role = Column(Enum(RoleType))
    
    # Foreign Keys
    block_id = Column(Integer, ForeignKey("blocks.id"))
    member_id = Column(Integer, ForeignKey("members.id"))
    
    # Relationships
    block = relationship("Block", back_populates="roles")
    member = relationship("Member")
    
    __table_args__ = (
        UniqueConstraint('block_id', 'role', name='_block_role_uc'),
    )

# -------------------
# Financial Tracking
# -------------------
class Meeting(Base):
    """
    A meeting is held weekly. Each meeting is associated with the umbrella and a particular block.
    The meeting host is a particular membership (i.e. a member in a given block).
    """
    __tablename__ = "meetings"
    
    id = Column(Integer, primary_key=True, index=True)
    meeting_date = Column(DateTime)
    scheduled_at = Column(DateTime, default=datetime.utcnow)
    
    # Foreign Keys
    block_id = Column(Integer, ForeignKey('blocks.id'), nullable=False, index=True)
    host_id = Column(Integer, ForeignKey('members.id'), nullable=False, index=True)
    
    # Relationships
    block = relationship("Block", back_populates="meetings")
    host = relationship("Member")
    contributions = relationship("Contribution", back_populates="meeting")

class Contribution(Base):
    __tablename__ = "contributions"
    
    id = Column(Integer, primary_key=True)
    amount = Column(Float)
    date = Column(DateTime)
    
    # Foreign Keys
    meeting_id = Column(Integer, ForeignKey("meetings.id"))
    payer_id = Column(Integer, ForeignKey("members.id"))
    block_id = Column(Integer, ForeignKey("blocks.id"))
    bank_id = Column(Integer, ForeignKey("banks.id"))
    
    # Relationships
    meeting = relationship("Meeting", back_populates="contributions")
    member = relationship("Member", back_populates="contributions")
    block = relationship("Block")


class Bank(Base):
    __tablename__ = 'banks'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    paybill_no = Column(String, nullable=False, unique=True)