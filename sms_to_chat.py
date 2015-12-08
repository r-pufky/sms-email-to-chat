#!/usr/bin/python
#
# Processes SmsMessagess and converts them to an adium log format.
#

import logging
import sys

import sms_email
import sms_users
import sms_interactions

reload(sys)
sys.setdefaultencoding('utf8')


class Message(object):
  """ Represents the actual chat conversation taking place.

  Attributes:
    to: User object the actual user sending the message.
    frome: User object the actual user recieving the message.
    timestamp: datetime object representing the time the message was sent.
    id: Integer SMS message id for ordering.
    thread: Integer SMS message thread for ordering.
    message: String actual SMS message sent.
  """

  def __init__(self, to, frome, timestamp, id, message):
    """ Create a basic generic message.

    Args:
      to: User object the actual user sending the message.
      frome: User object the actual user recieving the message.
      timestamp: datetime object representing the time the message was sent.
      id: Integer SMS message id for ordering.
      message: String actual SMS message sent.
    """
    self.to = to
    self.frome = frome
    self.timestamp = timestamp
    self.id = id
    self.message = message

  def LogDate(self):
    """ Returns the datetime of the message in log format.

    Format is: 2006-07-14T12:42:01-05:00 (YYYY-MM-DDTHH:MM:SSMMM-TZ)
    """
    return self.timestamp.isoformat()

  def __str__(self):
    return '%s' % self.id

  def __repr__(self):
    return '%s' % self.id

  def __eq__(self, other):
    return (self.id == other.id and
            self.timestamp == other.timestamp and
            self.message == other.message and
            self.to == other.to and
            self.frome == other.frome)

  def __hash__(self):
    return hash((self.id, self.timestamp, self.message, self.to, self.frome))


class AdiumLogExporter(object):
  """ Creates adium XML 0.4 logs for export. """
  _CHAT_HEADER = '<chat account="%s" service="SMS" version="0.4">'
  _CHAT_OPEN = '  <event type="windowsOpened" time="%s"/>'
  _CHAT_MESSAGE = '  <message sender="%s" time="%s">%s</message>'
  _CHAT_CLOSE = '  <event type="windowClosed" time="%s"/>'
  _CHAT_FOOTER = '</chat>'

  def _LogStart(self, message):
    """ Returns a list representing the start of a chat log. """
    log = []
    log.append(self._CHAT_HEADER % message.frome)
    log.append(self._CHAT_OPEN % message.LogDate())
    log.append(self._CHAT_MESSAGE % (
        message.frome, message.LogDate(), message.message))
    return log

  def _LogFinish(self, message):
    """ Returns a list representing the end of a chat log. """
    log = []
    log.append(self._CHAT_MESSAGE % (
        message.frome, message.LogDate(), message.message))
    log.append(self._CHAT_CLOSE % message.LogDate())
    return log

  def Convert(self, messages):
    """ Generates a adium XML 0.4 compliant log.

    Messages are de-duplicated, and sorted before processing into a log.

    Args:
      messages: List of sms_to_chat.Messages to generate log for.

    Returns:
      Tuple (initial date, finish date, user1, user2, log)
    """
    logging.info('unsorted messages: %s', messages)
    messages = list(set(messages))
    messages.sort(key=lambda x: x.id)
    logging.info('sorted / de-duplicated messages: %s', messages)
    log = []
    total = len(messages)
    for i in range(total):
      if i == 0:
        log.extend(self._LogStart(messages[i]))
        initial_date = messages[i].timestamp
      elif i == total-1:
        log.extend(self._LogFinish(messages[i]))
        finish_date = messages[i].timestamp
      else:
        log.append(self._CHAT_MESSAGE % (
            messages[i].frome, messages[i].LogDate(), messages[i].message))
    log.append(self._CHAT_FOOTER)
    if total == 1:
      finish_date = messages[0].timestamp
    return (initial_date, finish_date, u'\n'.join(log))


class SmsToChat(object):
  """ Converts maildir containg SMS-backup-plus emails to an adium chat log.
  
  Attributes:
    smss: List of all maildir email SmsMessage object imports.
    interactions: Interactions object managing hash ID's for conversations
    users: List of all rich-data user metadata from maildir imports.
    convos: Dictionary of processed sms/email messages, indexed by interaction
      ID, thread ID, then sorted by message ID.
  
  """

  def __init__(self, maildir, timezone):
    self.smss = sms_email.LoadMaildir(maildir, timezone)
    self.interactions = sms_interactions.Interactions()
    self.users = sms_users.Users()
    self.convos = {}
    self.log_exporter = AdiumLogExporter()

  def _IndexUsers(self):
    """ Indexes Users from SMS messages.
    
    This generates a complete 'user' picture per user, then
    creates UUID's for each specific user/user interaction.
    """
    print 'Indexing user metadata ...'
    for mail in self.smss:
      self.users.Update(mail.GetSender())
      self.users.Update(mail.GetReceiver())
    self.users.ProcessPartialUsers()
    for mail in self.smss:
      user1 = self.users.Find(mail.GetSender())
      user2 = self.users.Find(mail.GetReceiver())
      self.interactions.Update(user1, user2)
      mail.uuid = self.interactions.Get(user1, user2)

  def _IndexMessages(self):
    """ Indexes SmsMessages into conversations for export.

    Includes the rich-data user information for to/from fields, and moves the
    data to a consumable format for chat-logging, removing SMS and email
    specific details. Resultant list of messages is *NOT* sorted by default.

    Returns:
      Dictionary containing user interaction pairs:
      {'interaction_uuid': {'thread': [message 1, message 2, message 3],
                            'thread2': ...},
       'interaction_uuid': ... }
    """
    self._IndexUsers()
    print 'Indexing %s messages ...' % len(self.smss)
    for mail in self.smss:
      from_user = self.users.Find(mail.GetSender())
      to_user = self.users.Find(mail.GetReceiver())
      sms = Message(to_user, from_user, mail.date, mail.id, mail.message)
      self.convos.setdefault(mail.uuid, {})
      self.convos[mail.uuid].setdefault(mail.thread, [])
      self.convos[mail.uuid][mail.thread].append(sms)

  def Process(self):
    self._IndexMessages()
    print 'Processing messages ...'
    chat_logs = []
    for convo in self.convos:
      for thread in self.convos[convo]:
        start, end, log = self.log_exporter.Convert(self.convos[convo][thread])
        logname = ('%s-%s-%s-%s.log.xml' % (convo, thread,
            start.strftime('%s'), end.strftime('%s')))
        chat_logs.append((logname, log))
    return chat_logs


if __name__ == '__main__':
  pass
