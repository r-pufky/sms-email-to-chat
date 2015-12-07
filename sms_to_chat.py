#!/usr/bin/python
#
# Processes SmsMessagess and converts them to an adium log format.
#

import logging

import sms_email
import sms_users
import sms_interactions


class SmsToChat(object):
  """ Converts maildir containg SMS-backup-plus emails to an adium chat log. """

  def __init__(self, maildir, timezone):
    self.smss = sms_email.LoadMaildir(maildir, timezone)
    self.interactions = sms_interactions.Interactions()
    self.users = sms_users.Users()

  def _IndexUsers(self):
    """ Indexes Users from SMS messages. """
    for mail in self.smss:
      self.users.Update(mail._GetSender())
      self.users.Update(mail._GetReceiver())
    self.users.ProcessPartialUsers()

  def _IndexMessages(self):
    """ Indexes SmsMessages into conversations for export.
    Returns:
      Dictionary containing user interaction pairs:
      {'interaction_uuid': {'thread': [message 1, message 2, message 3],
                            'thread2': ...},
       'interaction_uuid': ... }
    """
    pass

  def Process(self):
    self._IndexUsers()

if __name__ == '__main__':
  pass
