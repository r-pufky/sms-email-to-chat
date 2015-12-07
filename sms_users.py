#!/usr/bin/python
#
# Manages users for SMS email message imports.
#

import logging
import phonenumbers


class Error(Exception):
  """ Base exception for library. """
  pass


class User(object):
  """ A SMS user.

  Attributes:
    name: String user's real name.
    email: String user's email address.
    phone: phonenumber.phonenumbers.PhoneNumber object. Assumes US format.
  """

  def __init__(self, phone=None, name=None, email=None):
    """ Initialize User.

    Args:
      phone: String or phonenumbers object containing phone number. String is
          parsed as a US phone number.
      name: String user name.
      email: String user email.
    """
    if isinstance(phone, phonenumbers.phonenumber.PhoneNumber):
      self.phone = phone
    elif phone is not None:
      self.phone = phonenumbers.parse(phone, "US")
    else:
      self.phone = None
    self.name = name
    self.email = email

  def Update(self, phone, name, email):
    """ Updates user object with new information, if non-duplicated.

    Args:
      phone: phonenumbers.phonenumber.PhoneNumber object.
      name: String user's real name.
      email: String user's email address.

    Raises:
      Error if there is non-duplicate data detected.
    """
    if phone:
      if self.phone != phone and self.phone is None:
        self.phone = phone
      elif self.phone != phone and self.phone is not None:
        logging.warning('Non-duplicate phone detected: %s %s for %s %s',
                        self.phone, phone, self.name, self.email)
        raise Error('Non-duplicate phone detected: %s %s for %s %s',
                    self.phone, phone, self.name, self.email)
    if name:
      if self.name != name and self.name is None:
        self.name = name
      elif self.name != name and self.name is not None:
        logging.warning('Non-duplicate name detected: %s %s for %s %s',
                        self.name, name, self.email, self.phone)
        raise Error('Non-duplicate name detected: %s %s for %s %s',
                    self.name, name, self.email, self.phone)
    if email:
      if self.email != email and self.email is None:
        self.email = email
      elif self.email != email and self.email is not None:
        logging.warning('Non-duplicate email detected: %s %s for %s %s',
                        self.email, email, self.name, self.phone)
        raise Error('Non-duplicate email detected: %s %s for %s %s',
                    self.email, email, self.name, self.phone)

  def __str__(self):
    return '(%s, %s, %s)' % (self.phone, self.name, self.email)

  def __repr__(self):
    return 'User(%s, %s, %s)' % (self.phone, self.name, self.email)


class Users(object):
  """ Manages User objects for SMS messages. """

  def __init__(self):
    self._users = []
    self._partial_users = []

  def _UpdateName(self, user, name):
    """ Updates the User object with name if it is a non-duplicate.

    Args:
      user: User object to update.
      name: String user's real name to update.
    """
    # Google Calendar sometimes receives as 'null'
    if name == 'null':
      name = None
    if user.name is None and name:
      user.name = name
    elif user.name and name and user.name != name:
      logging.warning('User has two names! %s %s', user, name)
      raise Error('User has two names! %s %s' % (user, name))

  def _UpdateEmail(self, user, email):
    """ Updates the User object with email if it is a non-duplicate.

    Args:
      user: User object to update.
      email: String user's email address to update.
    """
    if user.email is None and email:
      user.email = email
    elif user.email and email and user.email != email:
      logging.warning('User has two emails! %s %s', user, email)
      raise Error('User has two emails! %s %s' % (user, email))

  def _UpdatePhone(self, user, phone):
    """ Updates the User object with phone if it is a non-duplicate.

    Args:
      user: User object to update.
      phone: String user's phone to update.
    """
    if user.phone is None and phone:
      user.phone = phone
    elif user.phone and phone and user.phone != phone:
      logging.warning('User has two phones! %s %s', user, phone)
      raise Error('User has two phones! %s %s' % (user, phone)) 

  def ProcessPartialUsers(self):
    """ Updates or adds a user to the list of Users.

    On update, all users are scanned for duplicate values, and modifications
    are made based on how strong the indicator is to identify the given user.

    phone
    email
    name

    The implicit assumption here is that a user doesn't have mulitple numbers
    or email addresses.

    Any user without a 'phone' is then added to the user list.
    """
    for partial_user in self._partial_users:
      for user in self._users:
        if user.phone == partial_user.phone and user.phone is not None:
          self._UpdateName(user, partial_user.name)
          self._UpdateEmail(user, partial_user.email)
          logging.warning('Partial user match on phone: %s / %s',
                          partial_user, user)
          continue
        if user.email == partial_user.email and user.email is not None:
          self._UpdatePhone(user, partial_user.phone)
          self._UpdateName(user, partial_user.name)
          logging.warning('Partial user match on email: %s / %s',
                          partial_user, user)
          continue
        if user.name == partial_user.name and user.name is not None:
          self._UpdatePhone(user, partial_user.phone)
          self._UpdateEmail(user, partial_user.email)
          logging.warning('Partial user match on name: %s / %s',
                          partial_user, user)
          continue
      self._users.append(partial_user)
      logging.warning('Partial user added to users: %s', partial_user)
    self._partial_users = []

  def Update(self, new_user):
    """ Updates or adds a user to the list of Users.

    Users are added if they have a phone. If they don't have a phone, they
    are added to the partial users list, which will dedup users using all
    avaliable information once all the user data is loaded.

    .Update((...))
    .ProcessPartialUsers()

    Args:
      new_user: User object containing information to update.
    """
    if new_user.phone is None:
      for user in self._partial_users:
        if (user.phone == new_user.phone and
            user.name == new_user.name and
            user.email == new_user.email):
          return
      self._partial_users.append(new_user)
      return
    for user in self._users:
      if user.phone == new_user.phone and user.phone is not None:
        self._UpdateName(user, new_user.name)
        self._UpdateEmail(user, new_user.email)
        return
    self._users.append(new_user)


if __name__ == '__main__':
  pass
