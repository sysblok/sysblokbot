import logging

from src.db.db_objects import TeamMember
from src.strings import load


logger = logging.getLogger(__name__)


class Role:
    @classmethod
    def get_name(cls) -> str:
        if not cls._name:
            raise NotImplementedError('')
        return cls._name

    @staticmethod
    def fits(member: TeamMember) -> bool:
        raise NotImplementedError('')


class RoleNewbie(Role):
    _name = 'newbie'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return member.status.lower() == load('sheets__team__status__newbie').lower()


class RoleActiveMember(Role):
    _name = 'active_member'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return member.status.lower() == load('sheets__team__status__active').lower()


class RoleFrozenMember(Role):
    _name = 'frozen_member'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return member.status.lower() == load('sheets__team__status__frozen').lower()


class RoleAuthor(Role):
    _name = 'author'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return RoleActiveMember.fits(member) and member.curator


class RoleRedactor(Role):
    _name = 'redactor'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return (
            RoleActiveMember.fits(member)
            and member.manager.lower() == load('sheets__team__manager__redactor').lower()
        )


class RoleIllustrator(Role):
    _name = 'illustrator'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return (
            RoleActiveMember.fits(member)
            and member.manager.lower() == load('sheets__team__manager__illustrator').lower()
        )


class RoleCommissioningEditor(Role):
    _name = 'commissioning_editor'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return (
            RoleActiveMember.fits(member)
            and member.manager.lower() == load('sheets__team__manager__editor').lower()
        )


class RoleDirector(Role):
    _name = 'director'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return (
            RoleActiveMember.fits(member)
            and member.manager.lower() == load('sheets__team__manager__director').lower()
        )


class RoleSoftwareEngineer(Role):
    _name = 'software_engineer'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return (
            RoleActiveMember.fits(member)
            and member.manager.lower() == load('sheets__team__manager__swe').lower()
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
    RoleSoftwareEngineer
]
