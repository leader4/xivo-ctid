# -*- coding: utf-8 -*-
import logging
from xivo_dao import queue_features_dao
from xivo_dao.queuestatisticdao import QueueStatisticDAO
from xivo_cti.model.queuestatistic import QueueStatistic
from xivo_cti.ami.ami_callback_handler import AMICallbackHandler
from xivo_cti.services.queuemember_service_notifier import QueueMemberServiceNotifier

logger = logging.getLogger("QueueStatisticsManager")

def register_events():
    callback_handler = AMICallbackHandler.get_instance()
    callback_handler.register_callback('QueueMemberStatus', parse_queue_member_status)
    callback_handler.register_callback('QueueMemberAdded', parse_queue_member_status)
    callback_handler.register_callback('QueueMemberRemoved', parse_queue_member_status)
    callback_handler.register_callback('QueueMemberPaused', parse_queue_member_status)

    queue_member_callback_handler = QueueMemberServiceNotifier.get_instance()
    queue_member_callback_handler.subscribe(parse_queue_member_update)


def parse_queue_member_status(event):
    try:
        manager = QueueStatisticsManager.get_instance()
        manager.get_queue_summary(event['Queue'])
    except (KeyError, ValueError):
        logger.warning('Failed to parse QueueSummary event %s', event)


def parse_queue_member_update(delta):
    manager = QueueStatisticsManager.get_instance()
    for queue_members in (delta.add, delta.change, delta.delete):
        for queue_member in queue_members.itervalues():
            manager.get_queue_summary(queue_member['queue_name'])


class QueueStatisticsManager(object):

    _instance = None

    def __init__(self):
        self._queue_statistic_dao = QueueStatisticDAO()

    def get_statistics(self, queue_name, xqos, window):
        queue_statistic = QueueStatistic()
        queue_statistic.received_call_count = self._queue_statistic_dao.get_received_call_count(queue_name, window)
        queue_statistic.answered_call_count = self._queue_statistic_dao.get_answered_call_count(queue_name, window)
        queue_statistic.abandonned_call_count = self._queue_statistic_dao.get_abandonned_call_count(queue_name, window)
        queue_statistic.max_hold_time = self._queue_statistic_dao.get_max_hold_time(queue_name, window)
        queue_statistic.mean_hold_time = self._queue_statistic_dao.get_mean_hold_time(queue_name, window)

        received_and_done = self._queue_statistic_dao.get_received_and_done(queue_name, window)

        if queue_statistic.answered_call_count:
            if received_and_done:
                queue_statistic.efficiency = int(round((float(queue_statistic.answered_call_count) / received_and_done * 100), 0))

            answered_in_qos = self._queue_statistic_dao.get_answered_call_in_qos_count(queue_name, window, xqos)
            queue_statistic.qos = int(round((float(answered_in_qos) / queue_statistic.answered_call_count * 100), 0))
        return queue_statistic

    def get_queue_summary(self, queue_name):
        if queue_features_dao.is_a_queue(queue_name):
            self.ami_wrapper.queuesummary(queue_name)

    def get_all_queue_summary(self):
        self.ami_wrapper.queuesummary()

    @classmethod
    def get_instance(cls):
        if cls._instance == None:
            cls._instance = cls()
        return cls._instance
