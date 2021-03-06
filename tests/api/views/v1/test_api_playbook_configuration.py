# -*- coding: utf-8 -*-
# Copyright (c) 2016 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for view for /v1/playbook_configuration API endpoint."""


import pytest

from decapod_common import playbook_plugin
from decapod_common import plugins
from decapod_common.models import playbook_configuration
from decapod_common.models import role
from decapod_common.models import server


@pytest.fixture
def mongo_collection(pymongo_connection, configure_model):
    return pymongo_connection.db.playbook_configuration


@pytest.fixture
def clean_pc_collection(mongo_collection):
    mongo_collection.remove({})


@pytest.fixture
def valid_post_request(new_cluster, new_servers, public_playbook_name):
    return {
        "name": pytest.faux.gen_alpha(),
        "playbook_id": public_playbook_name,
        "cluster_id": new_cluster.model_id,
        "server_ids": [srv.model_id for srv in new_servers],
        "hints": []
    }


@pytest.fixture
def config():
    return {
        pytest.faux.gen_alpha(): pytest.faux.gen_alphanumeric()
    }


@pytest.fixture
def pcmodel(new_cluster, new_servers, config, public_playbook_name):
    model = playbook_configuration.PlaybookConfigurationModel.create(
        name=pytest.faux.gen_alpha(),
        playbook_id=public_playbook_name,
        cluster=new_cluster,
        servers=new_servers,
        initiator_id=pytest.faux.gen_uuid()
    )
    model.configuration = config
    model.save()

    return model


def create_server():
    return server.ServerModel.create(
        pytest.faux.gen_uuid(),
        pytest.faux.gen_alphanumeric(),
        pytest.faux.gen_alphanumeric(),
        pytest.faux.gen_alphanumeric(),
        pytest.faux.gen_ipaddr(),
        initiator_id=pytest.faux.gen_uuid()
    )


def get_playbook_plug(public_playbook_name):
    plug = plugins.get_public_playbook_plugins()
    plug = plug[public_playbook_name]

    return plug


def test_api_get_access(sudo_client_v1, client_v1, normal_user):
    response = client_v1.get("/v1/playbook_configuration/")
    assert response.status_code == 401
    assert response.json["error"] == "Unauthorized"

    client_v1.login(normal_user.login, "qwerty")
    response = client_v1.get("/v1/playbook_configuration/")
    assert response.status_code == 403
    assert response.json["error"] == "Forbidden"

    response = sudo_client_v1.get("/v1/playbook_configuration/")
    assert response.status_code == 200


def test_get_playbook_configuration(
    sudo_client_v1, clean_pc_collection, new_cluster, new_servers,
    public_playbook_name, pcmodel, freeze_time
):
    pcmodel.save()

    response = sudo_client_v1.get("/v1/playbook_configuration/")
    assert response.status_code == 200
    assert response.json["total"] == 1
    assert len(response.json["items"]) == 1

    response_model = response.json["items"][0]
    assert response_model["model"] == \
        playbook_configuration.PlaybookConfigurationModel.MODEL_NAME
    assert response_model["id"] == pcmodel.model_id
    assert response_model["time_updated"] == int(freeze_time.return_value)
    assert response_model["time_deleted"] == 0
    assert response_model["data"]["cluster_id"] == new_cluster.model_id
    assert response_model["version"] == 3

    response = sudo_client_v1.get(
        "/v1/playbook_configuration/{0}/".format(response_model["id"])
    )
    assert response.status_code == 200
    assert response.json == response_model

    response = sudo_client_v1.get(
        "/v1/playbook_configuration/{0}/version/".format(response_model["id"])
    )
    assert response.status_code == 200
    assert response.json["total"] == 3
    assert len(response.json["items"]) == 3
    assert response.json["items"][0] == response_model

    response = sudo_client_v1.get(
        "/v1/playbook_configuration/{0}/version/3/".format(
            response_model["id"])
    )
    assert response.status_code == 200
    assert response.json == response_model

    response = sudo_client_v1.get(
        "/v1/playbook_configuration/{0}/version/20/".format(
            response_model["id"])
    )
    assert response.status_code == 404


def test_create_new_playbook_configuration(
    sudo_client_v1, normal_user, client_v1, valid_post_request
):
    response = client_v1.post("/v1/playbook_configuration/",
                              data=valid_post_request)
    assert response.status_code == 401

    client_v1.login(normal_user.login, "qwerty")
    response = client_v1.post("/v1/playbook_configuration/",
                              data=valid_post_request)
    assert response.status_code == 403

    response = sudo_client_v1.post("/v1/playbook_configuration/",
                                   data=valid_post_request)
    assert response.status_code == 200
    for key in "name", "playbook_id":
        assert response.json["data"][key] == valid_post_request[key]
    assert response.json["data"]["created_execution_id"] is None

    assert isinstance(response.json["data"]["configuration"], dict)


def test_create_and_run_new_playbook_configuration_nok(
        sudo_client_v1, valid_post_request):
    valid_post_request["run"] = True

    items_before = sudo_client_v1.get("/v1/playbook_configuration/")
    response = sudo_client_v1.post("/v1/playbook_configuration/",
                                   data=valid_post_request)
    items_after = sudo_client_v1.get("/v1/playbook_configuration/")

    assert response.status_code == 403
    assert items_before.json == items_after.json


def test_create_and_run_new_playbook_configuration_ok(
        sudo_client_v1, sudo_role, valid_post_request):
    valid_post_request["run"] = True

    role.PermissionSet.add_permission(
        "playbook", valid_post_request["playbook_id"])
    sudo_role.add_permissions("playbook", [valid_post_request["playbook_id"]])
    sudo_role.save()

    response = sudo_client_v1.post("/v1/playbook_configuration/",
                                   data=valid_post_request)
    assert response.status_code == 200
    assert response.json["data"]["created_execution_id"]

    response2 = sudo_client_v1.get(
        "/v1/execution/{0}/".format(
            response.json["data"]["created_execution_id"]))
    assert response2.status_code == 200
    assert response2.json["data"]["state"] == "created"


def test_create_new_playbook_configuration_unknown_playbook(
    sudo_client_v1, valid_post_request
):
    valid_post_request["playbook_id"] = pytest.faux.gen_alphanumeric()

    response = sudo_client_v1.post("/v1/playbook_configuration/",
                                   data=valid_post_request)
    assert response.status_code == 400
    assert response.json["error"] == "UnknownPlaybookError"


@pytest.mark.parametrize("server_list", (True, False))
def test_create_new_playbook_configuration_not_required_server_list(
    server_list, sudo_client_v1, valid_post_request, new_cluster
):
    plug = get_playbook_plug(valid_post_request["playbook_id"])
    plug.return_value.REQUIRED_SERVER_LIST = False

    if server_list:
        valid_post_request["server_ids"] = []
    else:
        valid_post_request["server_ids"].pop()

    response = sudo_client_v1.post("/v1/playbook_configuration/",
                                   data=valid_post_request)
    assert response.status_code == 200


def test_create_new_playbook_configuration_required_server_list_ok(
    sudo_client_v1, valid_post_request
):
    plug = get_playbook_plug(valid_post_request["playbook_id"])
    plug.return_value.REQUIRED_SERVER_LIST = True

    valid_post_request["server_ids"].pop()

    response = sudo_client_v1.post("/v1/playbook_configuration/",
                                   data=valid_post_request)
    assert response.status_code == 200


def test_create_new_playbook_configuration_required_server_list_fail(
    sudo_client_v1, valid_post_request
):
    plug = get_playbook_plug(valid_post_request["playbook_id"])
    plug.return_value.REQUIRED_SERVER_LIST = True

    valid_post_request["server_ids"] = []

    response = sudo_client_v1.post("/v1/playbook_configuration/",
                                   data=valid_post_request)
    assert response.status_code == 400
    assert response.json["error"] == "ServerListIsRequiredForPlaybookError"


def test_create_new_playbook_configuration_unknown_cluster(
    sudo_client_v1, valid_post_request
):
    valid_post_request["cluster_id"] = pytest.faux.gen_uuid()
    response = sudo_client_v1.post("/v1/playbook_configuration/",
                                   data=valid_post_request)
    assert response.status_code == 400
    assert response.json["error"] == "UnknownClusterError"


def test_create_new_playbook_configuration_deleted_cluster(
    sudo_client_v1, valid_post_request, new_cluster, new_servers
):
    new_cluster.remove_servers(new_servers)
    new_cluster.save()
    new_cluster.delete()

    response = sudo_client_v1.post("/v1/playbook_configuration/",
                                   data=valid_post_request)
    assert response.status_code == 400
    assert response.json["error"] == "UnknownClusterError"


def test_create_new_playbook_configuration_failed_policy_check(
    sudo_client_v1, normal_user, client_v1, valid_post_request,
        new_cluster, new_servers, public_playbook_name
):
    plug = get_playbook_plug(public_playbook_name)
    plug.return_value.SERVER_LIST_POLICY = \
        playbook_plugin.ServerListPolicy.not_in_any_cluster
    response = sudo_client_v1.post("/v1/playbook_configuration/",
                                   data=valid_post_request)
    assert response.status_code == 400


def test_update_playbook_configuration_access(
    sudo_client_v1, client_v1, normal_user, pcmodel
):
    api_model = pcmodel.make_api_structure()

    response = client_v1.put(
        "/v1/playbook_configuration/{0}/".format(api_model["id"]),
        data=api_model
    )
    assert response.status_code == 401

    client_v1.login(normal_user.login, "qwerty")
    response = client_v1.put(
        "/v1/playbook_configuration/{0}/".format(api_model["id"]),
        data=api_model
    )
    assert response.status_code == 403

    response = sudo_client_v1.put(
        "/v1/playbook_configuration/{0}/".format(api_model["id"]),
        data=api_model
    )
    assert response.status_code == 200
    assert response.json["version"] == 3
    assert response.json["data"] == api_model["data"]


@pytest.mark.parametrize("fieldnames", (
    ("configuration",),
    ("name",),
    ("configuration", "name"),
    []
))
def test_update_playbook_configuration_fieldnames(
    fieldnames, sudo_client_v1, pcmodel
):
    api_model = pcmodel.make_api_structure()

    for fieldname in fieldnames:
        if fieldname == "name":
            api_model["data"]["name"] = pytest.faux.gen_alpha()
        else:
            api_model["data"]["configuration"] = {
                pytest.faux.gen_alpha(): pytest.faux.gen_alphanumeric()
            }

    response = sudo_client_v1.put(
        "/v1/playbook_configuration/{0}/".format(api_model["id"]),
        data=api_model
    )
    assert response.status_code == 200
    assert response.json["version"] == 3
    assert response.json["data"] == api_model["data"]


def test_delete_playbook_configuration_ok(sudo_client_v1, pcmodel):
    response = sudo_client_v1.delete(
        "/v1/playbook_configuration/{0}/".format(pcmodel.model_id),
    )
    assert response.status_code == 200


def test_delete_playbook_configuration_nok(sudo_client_v1, pcmodel):
    pcmodel.delete()

    response = sudo_client_v1.delete(
        "/v1/playbook_configuration/{0}/".format(pcmodel.model_id),
    )
    assert response.status_code == 400
