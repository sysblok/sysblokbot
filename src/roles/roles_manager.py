import datetime
import json
import logging

from .roles import all_roles, Role

from src.db.db_client import DBClient
from src.db.db_objects import TeamMember
from src.utils.singleton import Singleton

logger = logging.getLogger(__name__)


class RolesManager(Singleton):
    def __init__(self, db_client: DBClient):
        if self.was_initialized():
            return
        self.db_client = db_client

    def fill_db_roles(self):
        members = self.db_client.get_all_members()
        member_roles = {}
        for member in members:
            roles = [role.get_name() for role in all_roles if role.fits(member)]
            member_roles[member.id] = roles
        self.db_client.fill_team_roles(member_roles)

    def get_roles_for_member(self, member_name: str) -> str:
        member = self.db_client.get_member_by_name(member_name)
        if not member:
            return 'Member not found'
        return ','.join(member.role)

    def get_members_for_role(self, role_name: str) -> str:
        members = self.db_client.get_members_for_role(role_name)
        return '\n'.join([member.name for member in members])
