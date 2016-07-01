# -*- coding: utf-8 -*-
import mimetypes
import os

from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from minio import Minio
from minio.error import ResponseError, InvalidXMLError
from urllib3.exceptions import MaxRetryError


def setting(name, default=None):
    """
    Helper function to get a Django setting by name or (optionally) return
    a default (or else ``None``).
    """
    return getattr(settings, name, default)


@deconstructible
class MinioStorage(Storage):
    server = setting('MINIO_SERVER')
    access_key = setting('MINIO_ACCESSKEY')
    secret_key = setting('MINIO_SECRET')
    bucket = setting('MINIO_BUCKET')
    secure = setting('MINIO_SECURE')

    def __init__(self, *args, **kwargs):
        super(MinioStorage, self).__init__(*args, **kwargs)
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            print('construct')
            self._connection = Minio(
                self.server, self.access_key, self.secret_key, self.secure)
        # self._connection.trace_on(sys.stdout)
        return self._connection

    def _bucket_has_object(self, name):
        try:
            self.connection.get_object(self.bucket, name)
            return True
        except (ResponseError, MaxRetryError) as err:
            # Exception rises when file not found.
            return False

    def _save(self, name, content):
        pathname, ext = os.path.splitext(name)
        dir_path, file_name = os.path.split(pathname)
        hashed_name = "{0}/{1}{2}".format(dir_path, hash(content), ext)
        if hasattr(content.file, 'content_type'):
            content_type = content.file.content_type
        else:
            content_type = mimetypes.guess_type(name)[0]
        try:
            self.connection.put_object(self.bucket, hashed_name, content, content.file.size, content_type=content_type)
        except InvalidXMLError as err:
            print(err)
        except MaxRetryError:
            pass
        return hashed_name

    def url(self, name):
        try:
            if self.connection.bucket_exists(self.bucket):
                return self.connection.presigned_get_object(self.bucket, name)
            else:
                return "image_not_found"
        except MaxRetryError:
            return "image_not_found"

    def exists(self, name):
        return self._bucket_has_object(name)
