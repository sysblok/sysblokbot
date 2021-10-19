import logging

from src.db.db_objects import TeamMember


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
        return member.status == 'испытательный'


class RoleActiveMember(Role):
    _name = 'active_member'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return member.status == 'в команде'


class RoleFrozenMember(Role):
    _name = 'frozen_member'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return member.status == 'заморозка'


class RoleAuthor(Role):
    _name = 'author'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return RoleActiveMember.fits(member) and member.curator


class RoleRedactor(Role):
    _name = 'redactor'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return RoleActiveMember.fits(member) and member.manager == 'Менеджер редакции'


class RoleIllustrator(Role):
    _name = 'illustrator'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return RoleActiveMember.fits(member) and member.manager == 'Бильд-менеджер'


class RoleCommissioningEditor(Role):
    _name = 'commissioning_editor'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return RoleActiveMember.fits(member) and member.manager == 'Менеджер выпуска'


class RoleDirector(Role):
    _name = 'director'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return RoleActiveMember.fits(member) and member.manager == 'Менеджер проекта'


class RoleSoftwareEngineer(Role):
    _name = 'software_engineer'

    @staticmethod
    def fits(member: TeamMember) -> bool:
        return RoleActiveMember.fits(member) and member.manager == 'Tech-менеджер'


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
