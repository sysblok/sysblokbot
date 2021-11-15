import datetime
import json
import logging
from typing import List, Optional

from .roles import all_roles, Role, Roles

from src.db.db_client import DBClient
from src.db.db_objects import TeamMember
from src.strings import load
from src.utils.singleton import Singleton

logger = logging.getLogger(__name__)


class RoleManager(Singleton):
    def __init__(self, db_client: DBClient):
        if self.was_initialized():
            return
        self.db_client = db_client

    def calculate_db_roles(self):
        members = self.db_client.get_all_members()
        member_roles = {}
        for member in members:
            roles = [role.get_name() for role in all_roles if role.fits(member)]
            member_roles[member.id] = roles
        self.db_client.fill_team_roles(member_roles)

    def get_member(self, member_name: str) -> Optional[TeamMember]:
        return self.db_client.get_member_by_name(member_name)

    def get_members_for_role(self, role_name: Roles) -> List[TeamMember]:
        return self.db_client.get_members_for_role(role_name.value)
