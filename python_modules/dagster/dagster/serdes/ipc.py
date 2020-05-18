import os
import sys
from collections import namedtuple
from contextlib import contextmanager
from time import sleep

from dagster import check
from dagster.core.errors import DagsterError
from dagster.serdes import (
    deserialize_json_to_dagster_namedtuple,
    serialize_dagster_namedtuple,
    whitelist_for_serdes,
)
from dagster.utils.error import serializable_error_info_from_exc_info


@whitelist_for_serdes
class IPCStartMessage(namedtuple('_IPCStartMessage', '')):
    def __new__(cls):
        return super(IPCStartMessage, cls).__new__(cls)


@whitelist_for_serdes
class IPCEndMessage(namedtuple('_IPCEndMessage', '')):
    def __new__(cls):
        return super(IPCEndMessage, cls).__new__(cls)


class DagsterIPCError(DagsterError):
    def __init__(self, message):
        self.message = message
        super(DagsterIPCError, self).__init__(message)


class FileBasedWriteStream:
    def __init__(self, file_path):
        check.str_param('file_path', file_path)
        self._file_path = file_path

    def send(self, dagster_named_tuple):
        _send(self._file_path, dagster_named_tuple)


def _send(file_path, obj):
    with open(os.path.abspath(file_path), 'a+') as fp:
        fp.write(serialize_dagster_namedtuple(obj) + '\n')


@contextmanager
def ipc_write_stream(file_path):
    check.str_param('file_path', file_path)
    _send(file_path, IPCStartMessage())
    try:
        yield FileBasedWriteStream(file_path)
    except Exception:  # pylint: disable=broad-except
        _send(file_path, serializable_error_info_from_exc_info(sys.exc_info()))
    finally:
        _send(file_path, IPCEndMessage())


def _process_line(file_pointer, sleep_interval=0.1):
    while True:
        line = file_pointer.readline()
        if line:
            return deserialize_json_to_dagster_namedtuple(line.rstrip())
        sleep(sleep_interval)


def ipc_read_event_stream(file_path, timeout=5):
    # Wait for file to be ready
    sleep_interval = 0.1
    elapsed_time = 0
    while elapsed_time < timeout and not os.path.exists(file_path):
        elapsed_time += sleep_interval
        sleep(sleep_interval)

    if not os.path.exists(file_path):
        raise DagsterIPCError("Timeout: read stream has not recieved any data in {timeout} seconds")

    with open(os.path.abspath(file_path), 'r') as file_pointer:
        message = _process_line(file_pointer)
        while elapsed_time < timeout and message == None:
            elapsed_time += sleep_interval
            sleep(sleep_interval)
            message = _process_line(file_pointer)

        # Process start message
        if not isinstance(message, IPCStartMessage):
            raise DagsterIPCError(
                "Attempted to read stream at file {file_path}, but first message was not an "
                "IPCStartMessage".format(file_path=file_path)
            )

        message = _process_line(file_pointer)
        while not isinstance(message, IPCEndMessage):
            yield message
            message = _process_line(file_pointer)