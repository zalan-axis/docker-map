# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import posixpath
from collections import namedtuple
import six

from ..functional import lazy_type, uses_type_registry


SharedVolume = namedtuple('SharedVolume', ('volume', 'readonly'))
ContainerLink = namedtuple('ContainerLink', ('container', 'alias'))
PortBinding = namedtuple('PortBinding', ('exposed_port', 'host_port', 'interface'))


CURRENT_DIR = '{0}{1}'.format(posixpath.curdir, posixpath.sep)


def _get_listed_tuples(value, element_type, conversion_func):
    if value is None:
        return []
    elif isinstance(value, element_type) or uses_type_registry(value):
        return [value]
    elif isinstance(value, six.string_types):
        return [conversion_func(value)]
    elif isinstance(value, (list, tuple)):
        return [conversion_func(e) for e in value]
    elif isinstance(value, dict):
        return [conversion_func(e) for e in six.iteritems(value)]
    raise ValueError("Invalid type; expected {0}, list, tuple, or dict; found {1}.".format(
        element_type.__name__, type(value).__name__))


def is_path(value):
    """
    Checks whether the given value represents a path, i.e. a string which starts with an indicator for absolute or
    relative paths.

    :param value: Value to check.
    :return: ``True``, if the value appears to be representing a path.
    :rtype: bool
    """
    return value and isinstance(value, six.string_types) and (value[0] == posixpath.sep or value[:2] == CURRENT_DIR)


def read_only(value):
    """
    Checks whether the given value indicates a read-only access for a volume. For simplicity, this is any
    ``True``-equivalent value that except for the string "rw" (read-write).

    :param value: Value to check.
    :return: ``True`` if the volume is to be read-only.
    :rtype: bool
    """
    return value and value != 'rw'


def get_list(value):
    """
    Wraps the given value in a list. ``None`` returns an empty list. Lists and tuples are returned as lists. Single
    strings and registered types are wrapped in a list.

    :param value: Value to return as a list.
    :return: List with the provided ``value``(s).
    :rtype: list
    """
    if value is None:
        return []
    elif isinstance(value, (list, tuple)):
        return list(value)
    elif isinstance(value, six.string_types + (lazy_type, )) or uses_type_registry(value):
        return [value]
    raise ValueError("Invalid type; expected a list, tuple, or string type, found {0}.".format(
        type(value).__name__))


def get_shared_volume(value):
    """
    Converts the given value to a ``SharedVolume`` tuple. It accepts strings, lists, tuples, and dicts as input.
    For lists and tuples, the first element is used as the volume alias, and the second (if present) as a read-only
    indicator. Same division goes for dicts, between key and value. Single values (strings, single-value tuples/lists)
    keep read-write-access.

    :param value: Input value for conversion.
    :return: SharedVolume tuple.
    :rtype: SharedVolume
    """
    if isinstance(value, SharedVolume):
        return value
    elif isinstance(value, six.string_types):
        return SharedVolume(value, False)
    elif isinstance(value, (list, tuple)):
        v_len = len(value)
        if v_len == 2:
            return SharedVolume(value[0], read_only(value[1]))
        elif v_len == 1:
            return SharedVolume(value[0], False)
        raise ValueError("Invalid element length; only tuples and lists of length 1-2 can be converted to a "
                         "SharedVolume tuple; found length {0}.".format(v_len))
    elif isinstance(value, dict):
        v_len = len(value)
        if v_len == 1:
            k, v = value.items()[0]
            return SharedVolume(k, read_only(v))
        raise ValueError("Invalid element length; only dicts with one element can be converted to a SharedVolume "
                         "tuple. Found length {0}.".format(v_len))
    raise ValueError("Invalid type; expected a list, tuple, or string type, found {0}.".format(type(value).__name__))


def _shared_host_volume_from_tuple(*values):
    v_len = len(values)
    if v_len == 3:
        return SharedVolume((values[0], values[1]), read_only(values[2]))
    elif v_len == 2:
        v0, v1 = values
        if isinstance(v1, (list, tuple)):
            sv_len = len(v1)
            v1_0 = v1[0]
            if sv_len == 2:
                return SharedVolume((v0, v1_0), read_only(v1[1]))
            elif sv_len == 1:
                if isinstance(v1_0, bool) or v1_0 in ('ro', 'rw'):
                    return SharedVolume(v0, read_only(v1_0))
                return SharedVolume((v0, v1_0), False)
            raise ValueError("Nested list in {0} must have exactly one or two entries; found "
                             "{1}.".format(values, sv_len))
        elif isinstance(v1, bool) or v1 in ('ro', 'rw'):
            return SharedVolume(v0, read_only(v1))
        return SharedVolume(values, False)
    elif v_len == 1:
        return SharedVolume(values[0], False)
    raise ValueError("Invalid element length; only tuples and lists of length 1-3 can be converted to a "
                     "SharedVolume tuple. Found length {0}.".format(v_len))


def get_shared_host_volume(value):
    """
    Converts the input to a ``SharedVolume`` tuple for a host bind. Input can be a single string, a list or tuple, or a
    single-entry dictionary.
    Single values are assumed to be volume aliases for read-write access. Tuples or lists with two elements, can be
    ``(alias, read-only indicator)``, or ``(container path, host path)``. The latter is assumed, unless the second
    element is boolean or a string of either ``ro`` or ``rw``, indicating read-only or read-write access for a volume
    alias. Three elements are always used as ``(container path, host path, read-only indicator)``.
    Nested values are unpacked, so that valid input formats are also ``{container path: (host path, read-only)}`` or
    ``(container_path: [host path, read-only])``.

    :param value: Input value for conversion.
    :return: A SharedVolume tuple
    :rtype: SharedVolume
    """
    if isinstance(value, SharedVolume):
        return value
    elif isinstance(value, six.string_types):
        return SharedVolume(value, False)
    elif isinstance(value, (list, tuple)):
        return _shared_host_volume_from_tuple(*value)
    elif isinstance(value, dict):
        v_len = len(value)
        if v_len == 1:
            c_path, v = value.items()[0]
            if isinstance(v, (list, tuple)):
                return _shared_host_volume_from_tuple(c_path, *v)
            return _shared_host_volume_from_tuple(c_path, v)
        raise ValueError("Invalid element length; only dicts with one element can be converted to a SharedVolume "
                         "tuple. Found length {0}.".format(v_len))
    raise ValueError("Invalid type; expected a list, tuple, or string type, found {0}.".format(type(value).__name__))


def get_container_link(value):
    """
    Converts the input to a ContainerLink tuple. It can be from a single string, list, or tuple. Single values (also
    single-element lists or tuples) are considered a simple container link, whereas two-element items are read as
    ``(linked container, alias name)``.

    :param value: Input value for conversion.
    :return: ContainerLink tuple.
    :rtype: ContainerLink
    """
    if isinstance(value, ContainerLink):
        return value
    elif isinstance(value, six.string_types):
        return ContainerLink(value, value)
    elif isinstance(value, (list, tuple)):
        v_len = len(value)
        if v_len == 2:
            return ContainerLink(*value)
        elif v_len == 1:
            return ContainerLink(value[0], value[0])
        raise ValueError("Invalid element length; only tuples and lists of length 1-2 can be converted to a "
                         "ContainerLink tuple. Found length {0}.".format(v_len))
    raise ValueError("Invalid type; expected a list, tuple, or string type, found {0}.".format(type(value).__name__))


def get_port_binding(value):
    """
    Converts the given value to a ``PortBinding`` tuple. Input may come as a single value (exposed port for container
    linking only), a two-element tuple/list (port published on all host interfaces) or a three-element tuple/list
    (port published on a particular host interface).

    :param value: Input value for conversion.
    :return: PortBinding tuple.
    :rtype: PortBinding
    """
    sub_types = six.string_types + (int, long)
    if isinstance(value, PortBinding):
        return value
    elif isinstance(value, sub_types):  # Port only
        return PortBinding(value, None, None)
    elif isinstance(value, (list, tuple)):  # Exposed port, host port, and possibly interface
        if len(value) == 1 and isinstance(value[0], sub_types):
            return PortBinding(value[0], None, None)
        if len(value) == 2:
            ex_port, host_bind = value
            if isinstance(host_bind, sub_types + (lazy_type, )) or host_bind is None or uses_type_registry(host_bind):
                # Port, host port
                return PortBinding(ex_port, host_bind, None)
            elif isinstance(host_bind, (list, tuple)) and len(host_bind) == 2:  # Port, (host port, interface)
                host_port, interface = host_bind
                return PortBinding(ex_port, host_port, interface)
            raise ValueError("Invalid sub-element type or length. Needs to be a port number or a tuple / list: "
                             "(port, interface).")
        elif len(value) == 3:
            ex_port, host_port, interface = value
            return PortBinding(ex_port, host_port, interface)
        raise ValueError("Invalid element length; only tuples and lists of length 2 or 3 can be converted to a "
                         "PortBinding tuple.")
    raise ValueError("Invalid type; expected a list, tuple, int or string type, found "
                     "{0}.".format(type(value).__name__))


def get_shared_volumes(value):
    """
    Converts a single value, a list or tuple, or a dictionary into a list of SharedVolume tuples.

    :param value: Input value to convert.
    :return: List of SharedVolume tuples.
    :rtype: list[SharedVolume]
    """
    return _get_listed_tuples(value, SharedVolume, get_shared_volume)


def get_shared_host_volumes(value):
    """
    Converts a single value, a list or tuple, or a dictionary into a list of SharedVolume tuples for host volumes.

    :param value: Input value to convert.
    :return: List of SharedVolume tuples.
    :rtype: list[SharedVolume]
    """
    return _get_listed_tuples(value, SharedVolume, get_shared_host_volume)


def get_container_links(value):
    """
    Converts a single value, a list or tuple, or a dictionary into a list of ContainerLink tuples.

    :param value: Input value to convert.
    :return: List of ContainerLink tuples.
    :rtype: list[ContainerLink]
    """
    return _get_listed_tuples(value, ContainerLink, get_container_link)


def get_port_bindings(value):
    """
    Converts a single value, a list or tuple, or a dictionary into a list of PortBinding tuples.

    :param value: Input value to convert.
    :return: List of PortBinding tuples.
    :rtype: list[PortBinding]
    """
    return _get_listed_tuples(value, PortBinding, get_port_binding)
