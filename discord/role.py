"""
The MIT License (MIT)

Copyright (c) 2015-present Rapptz

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, TypeVar, Union, overload, TYPE_CHECKING

from .permissions import Permissions
from .errors import InvalidArgument
from .colour import Colour
from .mixins import Hashable
from .utils import snowflake_time, _get_as_snowflake, MISSING
from .asset import Asset

__all__ = (
    'RoleTags',
    'Role',
)

if TYPE_CHECKING:
    import datetime
    from .types.role import (
        Role as RolePayload,
        RoleTags as RoleTagPayload,
    )
    from .types.guild import RolePositionUpdate
    from .guild import Guild
    from .member import Member
    from .state import ConnectionState


class RoleTags:
    """Represents tags on a role.

    A role tag is a piece of extra information attached to a managed role
    that gives it context for the reason the role is managed.

    While this can be accessed, a useful interface is also provided in the
    :class:`Role` and :class:`Guild` classes as well.

    .. versionadded:: 1.6

    Attributes
    ------------
    bot_id: Optional[:class:`int`]
        The bot's user ID that manages this role.
    integration_id: Optional[:class:`int`]
        The integration ID that manages the role.
    """

    __slots__ = (
        'bot_id',
        'integration_id',
        '_premium_subscriber',
    )

    def __init__(self, data: RoleTagPayload):
        self.bot_id: Optional[int] = _get_as_snowflake(data, 'bot_id')
        self.integration_id: Optional[int] = _get_as_snowflake(data, 'integration_id')
        # NOTE: The API returns "null" for this if it's valid, which corresponds to None.
        # This is different from other fields where "null" means "not there".
        # So in this case, a value of None is the same as True.
        # Which means we would need a different sentinel.
        self._premium_subscriber: Optional[Any] = data.get('premium_subscriber', MISSING)

    def is_bot_managed(self) -> bool:
        """:class:`bool`: Whether the role is associated with a bot."""
        return self.bot_id is not None

    def is_premium_subscriber(self) -> bool:
        """:class:`bool`: Whether the role is the premium subscriber, AKA "boost", role for the guild."""
        return self._premium_subscriber is None

    def is_integration(self) -> bool:
        """:class:`bool`: Whether the role is managed by an integration."""
        return self.integration_id is not None

    def __repr__(self) -> str:
        return (
            f'<RoleTags bot_id={self.bot_id} integration_id={self.integration_id} '
            f'premium_subscriber={self.is_premium_subscriber()}>'
        )


R = TypeVar('R', bound='Role')


class Role(Hashable):
    """Represents a Discord role in a :class:`Guild`.

    .. container:: operations

        .. describe:: x == y

            Checks if two roles are equal.

        .. describe:: x != y

            Checks if two roles are not equal.

        .. describe:: x > y

            Checks if a role is higher than another in the hierarchy.

        .. describe:: x < y

            Checks if a role is lower than another in the hierarchy.

        .. describe:: x >= y

            Checks if a role is higher or equal to another in the hierarchy.

        .. describe:: x <= y

            Checks if a role is lower or equal to another in the hierarchy.

        .. describe:: hash(x)

            Return the role's hash.

        .. describe:: str(x)

            Returns the role's name.

    Attributes
    ----------
    id: :class:`int`
        The ID for the role.
    name: :class:`str`
        The name of the role.
    guild: :class:`Guild`
        The guild the role belongs to.
    hoist: :class:`bool`
         Indicates if the role will be displayed separately from other members.
    position: :class:`int`
        The position of the role. This number is usually positive. The bottom
        role has a position of 0.

        .. warning::

            Multiple roles can have the same position number. As a consequence
            of this, comparing via role position is prone to subtle bugs if
            checking for role hierarchy. The recommended and correct way to
            compare for roles in the hierarchy is using the comparison
            operators on the role objects themselves.

    managed: :class:`bool`
        Indicates if the role is managed by the guild through some form of
        integrations such as Twitch.
    mentionable: :class:`bool`
        Indicates if the role can be mentioned by users.
    tags: Optional[:class:`RoleTags`]
        The role tags associated with this role.
    """

    __slots__ = (
        'id',
        'name',
        '_permissions',
        '_colour',
        'position',
        'managed',
        'mentionable',
        'hoist',
        'guild',
        'tags',
        '_state',
        '_icon',
    )

    def __init__(self, *, guild: Guild, state: ConnectionState, data: RolePayload):
        self.guild: Guild = guild
        self._state: ConnectionState = state
        self.id: int = int(data['id'])
        self._update(data)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'<Role id={self.id} name={self.name!r}>'

    def __lt__(self: R, other: R) -> bool:
        if not isinstance(other, Role) or not isinstance(self, Role):
            return NotImplemented

        if self.guild != other.guild:
            raise RuntimeError('cannot compare roles from two different guilds.')

        # the @everyone role is always the lowest role in hierarchy
        guild_id = self.guild.id
        if self.id == guild_id:
            # everyone_role < everyone_role -> False
            return other.id != guild_id

        if self.position < other.position:
            return True

        if self.position == other.position:
            return int(self.id) > int(other.id)

        return False

    def __le__(self: R, other: R) -> bool:
        r = Role.__lt__(other, self)
        if r is NotImplemented:
            return NotImplemented
        return not r

    def __gt__(self: R, other: R) -> bool:
        return Role.__lt__(other, self)

    def __ge__(self: R, other: R) -> bool:
        r = Role.__lt__(self, other)
        if r is NotImplemented:
            return NotImplemented
        return not r

    def _update(self, data: RolePayload):
        self.name: str = data['name']
        self._permissions: int = int(data.get('permissions', 0))
        self.position: int = data.get('position', 0)
        self._colour: int = data.get('color', 0)
        self.hoist: bool = data.get('hoist', False)
        self.managed: bool = data.get('managed', False)
        self.mentionable: bool = data.get('mentionable', False)
        self._icon: Optional[str] = data.get('icon', None)
        self.tags: Optional[RoleTags]

        try:
            self.tags = RoleTags(data['tags'])
        except KeyError:
            self.tags = None

    def is_default(self) -> bool:
        """:class:`bool`: Checks if the role is the default role."""
        return self.guild.id == self.id

    def is_bot_managed(self) -> bool:
        """:class:`bool`: Whether the role is associated with a bot.

        .. versionadded:: 1.6
        """
        return self.tags is not None and self.tags.is_bot_managed()

    def is_premium_subscriber(self) -> bool:
        """:class:`bool`: Whether the role is the premium subscriber, AKA "boost", role for the guild.

        .. versionadded:: 1.6
        """
        return self.tags is not None and self.tags.is_premium_subscriber()

    def is_integration(self) -> bool:
        """:class:`bool`: Whether the role is managed by an integration.

        .. versionadded:: 1.6
        """
        return self.tags is not None and self.tags.is_integration()

    def is_assignable(self) -> bool:
        """:class:`bool`: Whether the role is able to be assigned or removed by the bot.

        .. versionadded:: 2.0
        """
        me = self.guild.me
        return not self.is_default() and not self.managed and (me.top_role > self or me.id == self.guild.owner_id)

    @property
    def permissions(self) -> Permissions:
        """:class:`Permissions`: Returns the role's permissions."""
        return Permissions(self._permissions)

    @property
    def colour(self) -> Colour:
        """:class:`Colour`: Returns the role colour. An alias exists under ``color``."""
        return Colour(self._colour)

    @property
    def color(self) -> Colour:
        """:class:`Colour`: Returns the role color. An alias exists under ``colour``."""
        return self.colour

    @property
    def created_at(self) -> datetime.datetime:
        """:class:`datetime.datetime`: Returns the role's creation time in UTC."""
        return snowflake_time(self.id)

    @property
    def mention(self) -> str:
        """:class:`str`: Returns a string that allows you to mention a role."""
        return f'<@&{self.id}>'

    @property
    def members(self) -> List[Member]:
        """List[:class:`Member`]: Returns all the members with this role."""
        all_members = self.guild.members
        if self.is_default():
            return all_members

        role_id = self.id
        return [member for member in all_members if member._roles.has(role_id)]
    
    @property
    def icon(self) -> Optional[Asset]:
        """Optional[:class:`Asset`]: Returns the role's icon asset, if available."""
        if self._icon is None:
            return None
        return Asset._from_icon(self._state, self.id, self._icon, 'role')

    async def _move(self, position: int, reason: Optional[str]) -> None:
        if position <= 0:
            raise InvalidArgument("Cannot move role to position 0 or below")

        if self.is_default():
            raise InvalidArgument("Cannot move default role")

        if self.position == position:
            return  # Save discord the extra request.

        http = self._state.http

        change_range = range(min(self.position, position), max(self.position, position) + 1)
        roles = [r.id for r in self.guild.roles[1:] if r.position in change_range and r.id != self.id]

        if self.position > position:
            roles.insert(0, self.id)
        else:
            roles.append(self.id)

        payload: List[RolePositionUpdate] = [{"id": z[0], "position": z[1]} for z in zip(roles, change_range)]
        await http.move_role_position(self.guild.id, payload, reason=reason)

    async def edit(
        self,
        *,
        name: str = MISSING,
        permissions: Permissions = MISSING,
        colour: Union[Colour, int] = MISSING,
        color: Union[Colour, int] = MISSING,
        hoist: bool = MISSING,
        mentionable: bool = MISSING,
        position: int = MISSING,
        reason: Optional[str] = MISSING,
    ) -> Optional[Role]:
        """|coro|

        Edits the role.

        You must have the :attr:`~Permissions.manage_roles` permission to
        use this.

        All fields are optional.

        .. versionchanged:: 1.4
            Can now pass ``int`` to ``colour`` keyword-only parameter.

        .. versionchanged:: 2.0
            Edits are no longer in-place, the newly edited role is returned instead.

        Parameters
        -----------
        name: :class:`str`
            The new role name to change to.
        permissions: :class:`Permissions`
            The new permissions to change to.
        colour: Union[:class:`Colour`, :class:`int`]
            The new colour to change to. (aliased to color as well)
        hoist: :class:`bool`
            Indicates if the role should be shown separately in the member list.
        mentionable: :class:`bool`
            Indicates if the role should be mentionable by others.
        position: :class:`int`
            The new role's position. This must be below your top role's
            position or it will fail.
        reason: Optional[:class:`str`]
            The reason for editing this role. Shows up on the audit log.

        Raises
        -------
        Forbidden
            You do not have permissions to change the role.
        HTTPException
            Editing the role failed.
        InvalidArgument
            An invalid position was given or the default
            role was asked to be moved.

        Returns
        --------
        :class:`Role`
            The newly edited role.
        """
        if position is not MISSING:
            await self._move(position, reason=reason)

        payload: Dict[str, Any] = {}
        if color is not MISSING:
            colour = color

        if colour is not MISSING:
            if isinstance(colour, int):
                payload['color'] = colour
            else:
                payload['color'] = colour.value

        if name is not MISSING:
            payload['name'] = name

        if permissions is not MISSING:
            payload['permissions'] = permissions.value

        if hoist is not MISSING:
            payload['hoist'] = hoist

        if mentionable is not MISSING:
            payload['mentionable'] = mentionable

        data = await self._state.http.edit_role(self.guild.id, self.id, reason=reason, **payload)
        return Role(guild=self.guild, data=data, state=self._state)

    async def delete(self, *, reason: Optional[str] = None) -> None:
        """|coro|

        Deletes the role.

        You must have the :attr:`~Permissions.manage_roles` permission to
        use this.

        Parameters
        -----------
        reason: Optional[:class:`str`]
            The reason for deleting this role. Shows up on the audit log.

        Raises
        --------
        Forbidden
            You do not have permissions to delete the role.
        HTTPException
            Deleting the role failed.
        """

        await self._state.http.delete_role(self.guild.id, self.id, reason=reason)
