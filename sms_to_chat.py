#!/usr/bin/python
#
# Processes SmsMessagess and converts them to an adium log format.
#

import logging

import sms_email
import sms_users
import sms_interactions


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

  def __str__(self):
    return '%s' % self.id

  def __repr__(self):
    return '%s' % self.id

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
    specific details.

    Returns:
      Dictionary containing user interaction pairs:
      {'interaction_uuid': {'thread': [message 1, message 2, message 3],
                            'thread2': ...},
       'interaction_uuid': ... }
    """
    self._IndexUsers()
    print 'Indexing messages ...'
    for m in self.smss:
      from_user = self.users.Find(m.GetSender())
      to_user = self.users.Find(m.GetReceiver())
      sms = Message(to_user, from_user, m.date, m.id, m.message)
      self.convos.setdefault(m.uuid, {})
      self.convos[m.uuid].setdefault(m.thread, [])
      self.convos[m.uuid][m.thread].append(sms)

    for convo in self.convos:
      for thread in self.convos[convo]:
        self.convos[convo][thread].sort(key=lambda x: x.id)


  def Process(self):
    self._IndexMessages()


if __name__ == '__main__':
  pass
