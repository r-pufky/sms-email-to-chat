#!/usr/bin/python
#
# Manages all user to user interactions.
#

import uuid


class Interactions(object):
  """ Manages all user to user interactions.

  An interaction is unique between two users, regardless of who is sending.

  A unique UUID is created for each 'interaction' which can be pulled by
  querying this object with two users in any order.
  """
  def __init__(self):
    self._usermap = {}

  def Update(self, user1, user2):
    """ Updates Interactions hashmaps with a new user interactions.

    This is not data destructive, and can be called multiple times.

    Args:
      user1: User object for the first user.
      user2: User object for the second user.
    """
    interaction_id = uuid.uuid4()
    self._usermap.setdefault('%s%s' % (user1, user2), interaction_id)
    self._usermap.setdefault('%s%s' % (user2, user1), interaction_id)

  def Get(self, user1, user2):
    """ Returns the interaction_id for a given interaction.

    Args:
      user1: User object for the first user.
      user2: User object for the second user.
    """
    return self._usermap['%s%s' % (user1, user2)]


if __name__ == '__main__':
  pass
