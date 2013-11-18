# -*- coding: utf-8 -*-

# Copyright (C) 2012-2013 Avencall
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

from xivo.pubsub import Pubsub
from xivo_bus.ctl.client import BusCtlClient
from xivo_bus.resources.agent.client import AgentClient
from xivo_cti import cti_config
from xivo_cti.amiinterpret import AMI_1_8
from xivo_cti.call_forms.call_form_result_handler import CallFormResultHandler
from xivo_cti.call_forms.dispatch_filter import DispatchFilter
from xivo_cti.call_forms.variable_aggregator import VariableAggregator
from xivo_cti.channel_updater import ChannelUpdater
from xivo_cti.cti.cti_message_formatter import CTIMessageFormatter
from xivo_cti.ctiserver import CTIServer
from xivo_cti.innerdata import Safe
from xivo_cti.interfaces.interface_ami import AMI
from xivo_cti.ioc.context import context
from xivo_cti.scheduler import Scheduler
from xivo_cti.services.agent.availability_computer import AgentAvailabilityComputer
from xivo_cti.services.agent.availability_notifier import AgentAvailabilityNotifier
from xivo_cti.services.agent.availability_updater import AgentAvailabilityUpdater
from xivo_cti.services.agent.executor import AgentExecutor
from xivo_cti.services.agent.manager import AgentServiceManager
from xivo_cti.services.agent.parser import AgentServiceCTIParser
from xivo_cti.services.agent.status_adapter import AgentStatusAdapter
from xivo_cti.services.agent.status_manager import AgentStatusManager
from xivo_cti.services.agent.status_parser import AgentStatusParser
from xivo_cti.services.agent.status_router import AgentStatusRouter
from xivo_cti.services.call.call_notifier import CallNotifier
from xivo_cti.services.call.endpoint_notifier import EndpointNotifier
from xivo_cti.services.call.receiver import CallReceiver
from xivo_cti.services.call.storage import CallStorage
from xivo_cti.services.current_call.formatter import CurrentCallFormatter
from xivo_cti.services.current_call.manager import CurrentCallManager
from xivo_cti.services.current_call.notifier import CurrentCallNotifier
from xivo_cti.services.current_call.parser import CurrentCallParser
from xivo_cti.services.device.manager import DeviceManager
from xivo_cti.services.funckey.manager import FunckeyManager
from xivo_cti.services.meetme.service_manager import MeetmeServiceManager
from xivo_cti.services.meetme.service_notifier import MeetmeServiceNotifier
from xivo_cti.services.presence.executor import PresenceServiceExecutor
from xivo_cti.services.presence.manager import PresenceServiceManager
from xivo_cti.services.queue.manager import QueueServiceManager
from xivo_cti.services.queue_entry_encoder import QueueEntryEncoder
from xivo_cti.services.queue_entry_manager import QueueEntryManager
from xivo_cti.services.queue_entry_notifier import QueueEntryNotifier
from xivo_cti.services.queue_member.cti.adapter import QueueMemberCTIAdapter
from xivo_cti.services.queue_member.cti.subscriber import \
    QueueMemberCTISubscriber
from xivo_cti.services.queue_member.manager import QueueMemberManager
from xivo_cti.services.queue_member.notifier import QueueMemberNotifier
from xivo_cti.services.queue_member.updater import QueueMemberUpdater
from xivo_cti.services.queue_member.indexer import QueueMemberIndexer
from xivo_cti.services.user.manager import UserServiceManager
from xivo_cti.services.user.notifier import UserServiceNotifier
from xivo_cti.statistics.queue_statistics_manager import QueueStatisticsManager
from xivo_cti.statistics.queue_statistics_producer import \
    QueueStatisticsProducer
from xivo_cti.statistics.statistics_notifier import StatisticsNotifier
from xivo_cti.statistics.statistics_producer_initializer import \
    StatisticsProducerInitializer
from xivo_cti.tools.delta_computer import DeltaComputer
from xivo_cti.xivo_ami import AMIClass


def setup():
    context.register('interface_ami', AMI)
    context.register('ami_18', AMI_1_8)
    context.register('ami_class', AMIClass)
    context.register('agent_availability_computer', AgentAvailabilityComputer)
    context.register('agent_availability_notifier', AgentAvailabilityNotifier)
    context.register('agent_availability_updater', AgentAvailabilityUpdater)
    context.register('agent_client', AgentClient)
    context.register('agent_executor', AgentExecutor)
    context.register('agent_service_cti_parser', AgentServiceCTIParser)
    context.register('agent_service_manager', AgentServiceManager)
    context.register('agent_status_adapter', AgentStatusAdapter)
    context.register('agent_status_manager', AgentStatusManager)
    context.register('agent_status_parser', AgentStatusParser)
    context.register('agent_status_router', AgentStatusRouter)
    context.register('bus_client', BusCtlClient)
    context.register('call_form_dispatch_filter', DispatchFilter)
    context.register('call_form_result_handler', CallFormResultHandler)
    context.register('call_form_variable_aggregator', VariableAggregator)
    context.register('call_notifier', CallNotifier)
    context.register('call_receiver', CallReceiver)
    context.register('call_storage', CallStorage)
    context.register('channel_updater', ChannelUpdater)
    context.register('config', cti_config.Config())
    context.register('cti_server', CTIServer)
    context.register('cti_message_formatter', CTIMessageFormatter)
    context.register('current_call_formatter', CurrentCallFormatter)
    context.register('current_call_manager', CurrentCallManager)
    context.register('current_call_notifier', CurrentCallNotifier)
    context.register('current_call_parser', CurrentCallParser)
    context.register('delta_computer', DeltaComputer)
    context.register('device_manager', DeviceManager)
    context.register('endpoint_notifier', EndpointNotifier)
    context.register('funckey_manager', FunckeyManager)
    context.register('innerdata', Safe)
    context.register('meetme_service_manager', MeetmeServiceManager)
    context.register('meetme_service_notifier', MeetmeServiceNotifier)
    context.register('presence_service_executor', PresenceServiceExecutor)
    context.register('presence_service_manager', PresenceServiceManager)
    context.register('pubsub', Pubsub)
    context.register('queue_entry_encoder', QueueEntryEncoder)
    context.register('queue_entry_manager', QueueEntryManager)
    context.register('queue_entry_notifier', QueueEntryNotifier)
    context.register('queue_service_manager', QueueServiceManager)
    context.register('queue_statistics_manager', QueueStatisticsManager)
    context.register('queue_statistics_producer', QueueStatisticsProducer)
    context.register('queue_member_cti_subscriber', QueueMemberCTISubscriber)
    context.register('queue_member_cti_adapter', QueueMemberCTIAdapter)
    context.register('queue_member_indexer', QueueMemberIndexer)
    context.register('queue_member_manager', QueueMemberManager)
    context.register('queue_member_notifier', QueueMemberNotifier)
    context.register('queue_member_updater', QueueMemberUpdater)
    context.register('statistics_notifier', StatisticsNotifier)
    context.register('scheduler', Scheduler)
    context.register('statistics_producer_initializer', StatisticsProducerInitializer)
    context.register('user_service_manager', UserServiceManager)
    context.register('user_service_notifier', UserServiceNotifier)
