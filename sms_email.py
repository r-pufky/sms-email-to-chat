#!/usr/bin/python
#
# Handles converting a mailbox.Maildir message to a usable Python object.
#
# References:
#   http://zedshaw.com/archive/curing-pythons-neglect/
#   https://pymotw.com/2/mailbox/
#   https://github.com/daviddrysdale/python-phonenumbers
#   https://stackoverflow.com/questions/4770297/python-convert-utc-datetime-string-to-local-datetime

import base64
import datetime
import logging
import mailbox
import phonenumbers
import pytz

import sms_users


class Error(Exception):
  """ Base exception for library. """
  pass


class InitError(Error):
  """ Exception during SMS message import. """
  pass


class LineToken(object):
  """ Process a given email line into given parsable tokens.

  Attributes:
    name: String Real Name in the line.
    email: String email in the line.
    phone: phonenumbers.phonenumber.PhoneNumber of phone number in the line.
  """

  def __init__(self, data):
    self.phone = None
    self.name = None
    self.email = None
    self.phone, self.name, self.email = self._ParsePhoneNameEmail(data)

  def _ParsePhoneNameEmail(self, raw_data):
    """ Parses data for a phone number, real name or email address.

    Handles:
      * All numbers only in all formats
      * email only
      * "Real Name" <email>
      * phone@unknown.person
      * email@domain@unknown.person

    Returns:
      tuple containing (phone, real name, email). Phone is phonenumbers object.
    """
    data = raw_data.strip()
    if '@unknown.person' in raw_data:
      data = data.rsplit('@', 1)[0]
    if 'SMS with ' in raw_data:
      data = data.split('SMS with ')[1].strip()

    try:
      return (phonenumbers.parse(data, 'US'), None, None)
    except:
      if "@" in data:
        if '<' in data and '>' in data:
          name_mail = data.split('<')
          return(None, name_mail[0].strip('" '), name_mail[1].strip('<> '))
        else:
          return (None, None, data)
      else:
        return (None, data, None)

  def __repr__(self):
    return '(%s, %s, %s)' % (self.phone, self.name, self.email)

  def __str__(self):
    return '(%s, %s, %s)' % (self.phone, self.name, self.email)


class SmsMessage(object):
  """ Stores a single SMS message converted from an email.

  datetimes in SMS message are stored in UTC as unixtimestamps in milliseconds.
 
  Attributes:
    to: LineToken 'to' field for email message.
    frome: LineToken 'from' field for email message.
    subject: LineToken 'subject' field for email message.
    id: Integer SMS message thread ID. Message order for a given thread.
    address: LineToken address of remote user (phone or email).
    type: Integer SMS message type. Default 1.
    date: Integer unix timestamp with milliseconds, actual SMS send datetime.
    thread: Integer representing a specific 'opened' chat between two users.
    read: Integer SMS message status. Default 1.
    status: Ineger TP-Status. Default -1.
    protocol: Integer SMS protocol. Default 0.
    service_center: LineToken service center message routed though.
      default: None.
    backup_time: Datetime string when sms-backup-plus synced message.
      default: None.
    content_type: String content type for message.
    message: String actual text message sent over SMS.
    tz: String timezone code for the message. Default 'Etc/UTC' (UTC).
    uuis: String interaction UUID for the message. Default None.
  """

  def __init__(self, email, tz='Etc/UTC', uuid=None):
    """ Creates a SmsMessage from a mailbox.MaildirMessage email.
    
    Args:
      email: mailbox.MaildirMessage SMS email to convert.
      tz: String timezone for messages. Default=Etc/UTC.

    Raises:
      InitError: If there was an error creating the object on import.
    """
    try:
      logging.info('SMS email date: %s', email['date'])
      self.to = LineToken(email['to'])
      self.frome = LineToken(email['from'])
      self.subject = LineToken(email['subject'])
      self.id = int(email['x-smssync-id'].strip())
      self.address = LineToken(email['x-smssync-address'])
      self.type = int(email.get('x-smssync-type'))
      self.date = (
          datetime.datetime(1970, 1, 1) +
          datetime.timedelta(milliseconds=int(email['x-smssync-date'].strip()))
          ).replace(tzinfo=pytz.UTC)
      self.thread = int(email['x-smssync-thread'])
      self.read = int(email.get('x-smssync-read', 1))
      self.status = int(email.get('x-smssync-status', -1))
      self.protocol = int(email.get('x-smssync-protocol', 0))
      self.service_center = LineToken(email.get('x-smssync-service_center', ''))
      self.content_type = email.get('content-type')
      self.message = base64.b64decode(email.fp.read()).strip()
      if not self.message:
        logging.warning('Empty SMS: %s; id: %s', self.date, self.id)
      self.tz = pytz.timezone(tz)
      self.uuid = None
    except KeyError, e:
      logging.critical('KeyError: %s', e)
      logging.critical('INVALID email: %s', email)
      raise InitError('INVALID SMS email: %s', email)

  def GetSender(self):
    """ Determines the sender of the message, based on message attributes.

    Filter everything we know about the sender into a tuple representing that
    user (phone, name, email).

    If self.type = 1, received from sync address (sender is sync address):
      address, subject, frome.
    If self.type = 2, sent to sync address (sender is NOT sync addres):
      frome field only.

    Most emails should have the same for multiple fields, so base process with
    that assumption.

    Assumption: We treat statuses 3-6 as 'sent', to keep log sane.
      3 - draft
      4 - outbox
      5 - failed
      6 - queued

    Returns:
      User object representing who sent the message.
    """
    phone = None
    name = None
    email = None

    if self.type == 1:
      authoritative = self.address
      phone_set = set(
          [self.address.phone, self.frome.phone, self.subject.phone])
      name_set = set(
          [self.address.name, self.frome.name, self.subject.name])
      email_set = set(
          [self.address.email, self.frome.email, self.subject.email])
    elif self.type > 1:
      authoritative = self.frome
      phone_set = set()
      name_set = set()
      email_set = set()
    else:
      logging.critical('SMS Type is not supported: %s', self.type)
      logging.critical('Details: %s, to: %s, from: %s, message: %s',
                       self.date, self.to, self.frome, self.message)
      raise TypeError('SMS Type is not supported: %s' % self.type)

    phones = []
    names = []
    emails = []
    for x in phone_set:
      if x is not None and x != '' and x != authoritative.phone:
        phones.append(x)
    for x in name_set:
      if x is not None and x != '' and x != authoritative.name:
        names.append(x)
    for x in email_set:
      if x is not None and x != '' and x != authoritative.email:
        emails.append(x)
    
    if len(phones) > 1 or len(names) > 1 or len(emails) > 1:
      logging.critical('Multiple non-duplicate user information: %s %s %s',
                       phones, names, emails)
      raise TypeError('Multiple non-duplicate user information: %s %s %s' %
                      (phones, names, emails))
    if not authoritative.phone and len(phones) > 0:
      phone = phones[0]
    else:
      phone = authoritative.phone
    if not authoritative.name and len(names) > 0:
      name = names[0]
    else:
      name = authoritative.name
    if not authoritative.email and len(emails) > 0:
      email = emails[0]
    else:
      email = authoritative.email
    return sms_users.User(phone, name, email)

  def GetReceiver(self):
    """ Determines the reciever the message, based on message attributes.

    Filter everything we know about the receiver into a tuple representing that
    user (phone, name, email).

    If self.type = 1, received from sync address (receiver is NOT sync address):
      to field only.
    If self.type = 2, sent to sync address (sender is sync addres):
      address, to, subject field.

    Most emails should have the same for multiple fields, so base process with
    that assumption.

    Assumption: We treat statuses 3-6 as 'sent', to keep log sane.
      3 - draft
      4 - outbox
      5 - failed
      6 - queued

    Returns:
      User object representing who sent the message.
    """
    phone = None
    name = None
    email = None
    if self.type == 1:
      authoritative = self.to
      phone_set = set()
      name_set = set()
      email_set = set()
    elif self.type > 1:
      authoritative = self.address
      phone_set = set(
          [self.address.phone, self.to.phone, self.subject.phone])
      name_set = set(
          [self.address.name, self.to.name, self.subject.name])
      email_set = set(
          [self.address.email, self.to.email, self.subject.email])
    else:
      logging.critical('SMS Type is not supported: %s', self.type)
      raise TypeError('SMS Type is not supported: %s' % self.type)

    phones = []
    names = []
    emails = []
    for x in phone_set:
      if x is not None and x != '' and x != authoritative.phone:
        phones.append(x)
    for x in name_set:
      if x is not None and x != '' and x != authoritative.name:
        names.append(x)
    for x in email_set:
      if x is not None and x != '' and x != authoritative.email:
        emails.append(x)
    
    if len(phones) > 1 or len(names) > 1 or len(emails) > 1:
      logging.critical('Multiple non-duplicate user information: %s %s %s',
                       phones, names, emails)
      raise TypeError('Multiple non-duplicate user information: %s %s %s' %
                      (phones, names, emails))
    if not authoritative.phone and len(phones) > 0:
      phone = phones[0]
    else:
      phone = authoritative.phone
    if not authoritative.name and len(names) > 0:
      name = names[0]
    else:
      name = authoritative.name
    if not authoritative.email and len(emails) > 0:
      email = emails[0]
    else:
      email = authoritative.email
    return sms_users.User(phone, name, email)


def LoadMaildir(maildir, timezone):
  """ Loads SMS messages from maildir email.

  Args:
    maildir: String location of maildir folder to process.
    timezone: String timezone to assume messages are received in.

  Returns:
    List of SmsMessage objects from email messages.
  """
  print 'Loading messages ...'
  mbox = mailbox.Maildir(maildir)
  sms_messages = []
  for email in mbox:
    sms_messages.append(SmsMessage(email, timezone))
  return sms_messages


if __name__ == '__main__':
  pass  
