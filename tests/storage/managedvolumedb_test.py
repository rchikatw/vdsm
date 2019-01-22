#
# Copyright 2019 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
#
# Refer to the README and COPYING files for full details of the license
#

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time
import uuid

from contextlib import closing
from datetime import datetime

import pytest

from vdsm.common import concurrent
from vdsm.storage import managedvolumedb


@pytest.fixture
def db_path(tmpdir, monkeypatch):
    db_file = str(tmpdir.join("managedvolumes.db"))
    monkeypatch.setattr(managedvolumedb, "DB_FILE", db_file)
    return db_file


@pytest.fixture
def tmp_db(db_path):
    managedvolumedb.create_db()


def test_create_db(db_path):
    managedvolumedb.create_db()
    # Now try some select from database. If we get NotFound, it means db file
    # and volumes db were created, which is what we want to test
    db = managedvolumedb.open()
    with closing(db):
        with pytest.raises(managedvolumedb.NotFound):
            db.get_volume("something")


def test_version_info(db_path):
    # sqlite doesn't store microseconds, so any non-zero value here can fail
    # the test
    start = datetime.utcnow().replace(microsecond=0)

    managedvolumedb.create_db()
    db = managedvolumedb.open()
    with closing(db):
        curr_version = db.version_info()

    assert managedvolumedb.VERSION == curr_version["version"]
    assert "Initial version" == curr_version["description"]
    assert start <= datetime.strptime(curr_version["updated"],
                                      "%Y-%m-%d %H:%M:%S")


def test_db_close(tmp_db):
    db = managedvolumedb.open()
    db.close()

    # tests that the connection is really close and no other operations
    # can be execute
    with pytest.raises(managedvolumedb.Closed):
        db.get_volume("something")


def test_insert_select(tmp_db):
    db = managedvolumedb.open()
    with closing(db):
        connection_info = {"key": "value"}
        test_id = str(uuid.uuid4())

        db.add_volume(test_id, connection_info)
        res = db.get_volume(test_id)

        assert res == {"connection_info": connection_info}


def test_insert_existing(tmp_db):
    connection_info = {"key": "value"}
    test_id = str(uuid.uuid4())

    db = managedvolumedb.open()
    with closing(db):
        db.add_volume(test_id, connection_info)

        connection_info2 = {"key2": "value2"}
        with pytest.raises(managedvolumedb.VolumeAlreadyExists):
            db.add_volume(test_id, connection_info2)


def test_get_non_existing(tmp_db):
    db = managedvolumedb.open()
    with closing(db):
        with pytest.raises(managedvolumedb.NotFound):
            db.get_volume("this doesn't exists")


def test_update(tmp_db):
    connection_info = {"key": "value"}
    test_id = str(uuid.uuid4())

    db = managedvolumedb.open()
    with closing(db):
        db.add_volume(test_id, connection_info)
        res = db.get_volume(test_id)

        assert res == {"connection_info": connection_info}

        path = "/dev/mapper/36001405376e34ea70384de7a34a2854d"
        multipath_id = "36001405376e34ea70384de7a34a2854d"
        attachment = {"key2": "value2"}
        db.update_volume(test_id, path, attachment, multipath_id)
        res = db.get_volume(test_id)

        expected = {"connection_info": connection_info,
                    "path": path,
                    "attachment": attachment,
                    "multipath_id": multipath_id}
        assert res == expected


def test_delete(tmp_db):
    connection_info = {"key": "value"}
    test_id = str(uuid.uuid4())

    db = managedvolumedb.open()
    with closing(db):
        db.add_volume(test_id, connection_info)
        res = db.get_volume(test_id)

        assert res["connection_info"]["key"] == "value"

        db.remove_volume(test_id)
        with pytest.raises(managedvolumedb.NotFound):
            db.get_volume(test_id)


def test_owns_multipath(tmp_db):
    vol_id = str(uuid.uuid4())
    connection_info = {"connection": 1}
    attachment = {"attachment": 2}
    path = "/dev/mapper/36001405376e34ea70384de7a34a2854d"
    multipath_id = "36001405376e34ea70384de7a34a2854d"

    db = managedvolumedb.open()
    with closing(db):
        # Empty db does not own any device.
        assert not db.owns_multipath(multipath_id)

        # Volume does not own (yet) multipath_id.
        db.add_volume(vol_id, connection_info)
        assert not db.owns_multipath(multipath_id)

        # Volume owns multipath_id.
        db.update_volume(vol_id, path, attachment, multipath_id)
        assert db.owns_multipath(multipath_id)

        # Nothing owns multipath_id now.
        db.remove_volume(vol_id)
        assert not db.owns_multipath(multipath_id)


@pytest.mark.slow
def test_concurrency(tmp_db):

    concurrency = 10
    iterations = 10

    # Sleeping this interval is enough to switch to another thread most of the
    # time based on the test logs.
    delay = 0.005

    vol_id_tmp = "%06d-%06d"

    def run(worker_id):
        for i in range(iterations):
            vol_id = vol_id_tmp % (worker_id, i)

            db = managedvolumedb.open()
            with closing(db):
                # Simulate attach volume flow.

                db.add_volume(vol_id, {"connection": vol_id})

                # Switch to another thread. Real code will wait for os_brick
                # several seconds here.
                time.sleep(delay)

                db.update_volume(
                    vol_id,
                    path="/dev/mapper/" + vol_id,
                    multipath_id=vol_id,
                    attachment={"attachment": vol_id})

            # Switch to another thread. Real code will process another
            # unrelated request here.
            time.sleep(delay)

    start = time.time()

    workers = []
    try:
        for i in range(concurrency):
            t = concurrent.thread(run, args=(i,))
            t.start()
            workers.append(t)
    finally:
        for t in workers:
            t.join()

    elapsed = time.time() - start

    volumes = concurrency * iterations
    print("Added %d volumes with %s concurrent threads in %.6f seconds "
          "(%.6f seconds/op)"
          % (volumes, concurrency, elapsed, elapsed / volumes))

    db = managedvolumedb.open()
    with closing(db):
        for i in range(concurrency):
            for j in range(iterations):
                vol_id = vol_id_tmp % (i, j)

                # Verify volume was added.
                vol_info = db.get_volume(vol_id)
                assert "connection_info" in vol_info

                # Verify volume was updated.
                assert "path" in vol_info
                assert "multipath_id" in vol_info
                assert "attachment" in vol_info
