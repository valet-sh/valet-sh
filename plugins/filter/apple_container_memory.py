#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.errors import AnsibleFilterError
from ansible.module_utils.common.text.formatters import human_to_bytes

MB = 1024 * 1024

DEFAULT_RESERVED_MB = 1024
DEFAULT_MAX_FRACTION = 0.5
DEFAULT_FLOOR_MB = 512
DEFAULT_CEILING_MB = 32000

def container_process_memory_mb(
    memory_limit,
    reserved_mb=DEFAULT_RESERVED_MB,
    max_fraction=DEFAULT_MAX_FRACTION,
    floor_mb=DEFAULT_FLOOR_MB,
    ceiling_mb=DEFAULT_CEILING_MB,
):
    try:
        limit_mb = human_to_bytes(str(memory_limit)) / MB
    except ValueError as exc:
        raise AnsibleFilterError("container_process_memory_mb: invalid memory limit '%s': %s" % (memory_limit, exc))

    budget_mb = min(limit_mb - reserved_mb, limit_mb * max_fraction, ceiling_mb)
    return int(max(budget_mb, floor_mb))


class FilterModule(object):
    def filters(self):
        return {"container_process_memory_mb": container_process_memory_mb}
