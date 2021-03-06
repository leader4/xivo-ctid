# -*- coding: utf-8 -*-

# Copyright (C) 2013-2014 Avencall
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

import logging

from xivo_cti import dao

logger = logging.getLogger(__name__)


class AgentStatusParser(object):

    def __init__(self, agent_status_manager, agent_status_adapter):
        self._agent_status_manager = agent_status_manager
        self._agent_status_adapter = agent_status_adapter

    def parse_ami_login(self, ami_event):
        agent_id = int(ami_event['AgentID'])
        self._agent_status_manager.agent_logged_in(agent_id)
        self._agent_status_adapter.subscribe_to_agent_events(agent_id)

    def parse_ami_logout(self, ami_event):
        agent_id = int(ami_event['AgentID'])
        self._agent_status_manager.agent_logged_out(agent_id)
        self._agent_status_adapter.unsubscribe_from_agent_events(agent_id)

    def parse_ami_paused(self, ami_event):
        agent_member_name = ami_event['MemberName']
        paused = ami_event['Paused'] == '1'
        try:
            agent_id = dao.agent.get_id_from_interface(agent_member_name)
        except ValueError:
            pass  # Not an agent member name
        else:
            if paused and dao.agent.is_completely_paused(agent_id):
                self._agent_status_manager.agent_paused_all(agent_id)
            else:
                self._agent_status_manager.agent_unpaused(agent_id)

    def parse_ami_acd_call_start(self, ami_event):
        agent_member_name = ami_event['MemberName']
        try:
            agent_id = dao.agent.get_id_from_interface(agent_member_name)
        except ValueError:
            pass  # Not an agent member name
        else:
            self._agent_status_manager.acd_call_start(agent_id)

    def parse_ami_acd_call_end(self, ami_event):
        wrapup = int(ami_event['WrapupTime'])
        agent_member_name = ami_event['MemberName']
        try:
            agent_id = dao.agent.get_id_from_interface(agent_member_name)
        except ValueError:
            pass  # Not an agent member name
        else:
            if wrapup > 0:
                self._agent_status_manager.agent_in_wrapup(agent_id, wrapup)
            else:
                self._agent_status_manager.acd_call_end(agent_id)
