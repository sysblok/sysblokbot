import logging
from enum import Enum

from src.db.db_objects import TeamMember
from src.strings import load

logger = logging.getLogger(__name__)


class Roles(str, Enum):
    NEWBIE = "newbie"
    ACTIVE_MEMBER = "active_member"
    FROZEN_MEMBER = "frozen_member"
    AUTHOR = "author"
    REDACTOR = "redactor"
    ILLUSTRATOR = "illustrator"
    COMMISSIONING_EDITOR = "commissioning_editor"
    DIRECTOR = "director"
    SOFTWARE_ENGINEER = "software_engineer"


class Role:
    @classmethod
    def get_name(cls) -> str:
        if not cls._name:
            raise NotImplementedError("")
        return cls._name

    @staticmethod
    def fits(member: TeamMember) -> bool:
        raise NotImplementedError("")


class RoleNewbie(Role):
    _name = Roles.NEWBIE

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return member.status.lower() == load("sheets__team__status__newbie").lower()


class RoleActiveMember(Role):
    _name = Roles.ACTIVE_MEMBER

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return member.status.lower() == load("sheets__team__status__active").lower()


class RoleFrozenMember(Role):
    _name = Roles.FROZEN_MEMBER

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return member.status.lower() == load("sheets__team__status__frozen").lower()


class RoleAuthor(Role):
    _name = Roles.AUTHOR

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return RoleActiveMember.fits(member) and member.curator


class RoleRedactor(Role):
    _name = Roles.REDACTOR

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return (
            RoleActiveMember.fits(member)
            and member.manager.lower()
            == load("sheets__team__manager__redactor").lower()
        )


class RoleIllustrator(Role):
    _name = Roles.ILLUSTRATOR

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return (
            RoleActiveMember.fits(member)
            and member.manager.lower()
            == load("sheets__team__manager__illustrator").lower()
        )


class RoleCommissioningEditor(Role):
    _name = Roles.COMMISSIONING_EDITOR

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return (
            RoleActiveMember.fits(member)
            and member.manager.lower() == load("sheets__team__manager__editor").lower()
        )


class RoleDirector(Role):
    _name = Roles.DIRECTOR

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return (
            RoleActiveMember.fits(member)
            and member.manager.lower()
            == load("sheets__team__manager__director").lower()
        )


class RoleSoftwareEngineer(Role):
    _name = Roles.SOFTWARE_ENGINEER

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return (
            RoleActiveMember.fits(member)
            and member.manager.lower() == load("sheets__team__manager__swe").lower()
        )


all_roles = [
    RoleNewbie,
    RoleActiveMember,
    RoleFrozenMember,
    RoleAuthor,
    RoleRedactor,
    RoleIllustrator,
    RoleCommissioningEditor,
    RoleDirector,
    RoleSoftwareEngineer,
]
