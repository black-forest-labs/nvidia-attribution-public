# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from attribution_blueprint import mca_registry as _registry
from attribution_blueprint.connectors.execution_contexts.kai.connector import (
    KaiExecutionContext,
    KaiExecutionContextAdapter,
)
from attribution_blueprint.exceptions import MCAError
from attribution_blueprint.kubernetes.daemon.config import (
    build_kubernetes_daemon_client,
)
from attribution_blueprint.mca_registry import _PARAM


def _build(spec: dict, ctx: dict) -> KaiExecutionContextAdapter:
    from attribution_blueprint.mca import _coerce_bool, _coerce_int

    # A literal `null` arrives as None and must fall back to the default;
    # otherwise None would reach the Kubernetes client and silently disable
    # the request timeout.
    timeout = spec.get("timeout_seconds")
    if timeout is None:
        timeout = 60
    else:
        timeout = _coerce_int(timeout, "eca.kai.timeout_seconds")
        if timeout <= 0:
            raise MCAError(f"eca.kai.timeout_seconds must be positive, got {timeout}")
    placement_records_enabled = _coerce_bool(
        spec.get("placement_records_enabled", False),
        "eca.kai.placement_records_enabled",
    )
    job_id_annotation = spec.get("job_id_annotation")
    if job_id_annotation is not None and (not isinstance(job_id_annotation, str) or not job_id_annotation.strip()):
        raise MCAError("eca.kai.job_id_annotation must be a non-empty string")
    daemon_spec = spec.get("kubernetes_daemon")
    if placement_records_enabled and daemon_spec is None:
        raise MCAError("eca.kai.placement_records_enabled requires eca.kai.kubernetes_daemon")
    if placement_records_enabled and not spec.get("namespace"):
        raise MCAError("eca.kai.placement_records_enabled requires eca.kai.namespace")
    return KaiExecutionContextAdapter(
        kubeconfig=spec.get("kubeconfig"),
        context=spec.get("context"),
        namespace=spec.get("namespace"),
        timeout_seconds=timeout,
        placement_records_enabled=placement_records_enabled,
        job_id_annotation=job_id_annotation,
        placement_reader=(
            build_kubernetes_daemon_client(
                daemon_spec,
                config_path="eca.kai.kubernetes_daemon",
            )
            if placement_records_enabled
            else None
        ),
    )


_registry.register_component(
    framework="eca",
    name="kai",
    schema={
        "ids": _PARAM,
        "start_time": _PARAM,
        "end_time": _PARAM,
        "nodelist": _PARAM,
        # Optional path to a kubeconfig file. When unset, the client falls back
        # to its default discovery (KUBECONFIG, ~/.kube/config, or the
        # in-cluster service account).
        "kubeconfig": _PARAM,
        # Optional context name within the resolved kubeconfig.
        "context": _PARAM,
        # Namespace scope. Required for time-range discovery and for bare
        # `<name>` IDs. Without it, ID discovery accepts only
        # `<namespace>/<name>`. The adapter never scans the whole cluster.
        "namespace": _PARAM,
        "timeout_seconds": _PARAM,
        "placement_records_enabled": _PARAM,
        # Pod annotation naming the job for PodGroups that no Job or JobSet
        # owns. Unset, such PodGroups are skipped.
        "job_id_annotation": _PARAM,
        "kubernetes_daemon": {
            "endpoint": _PARAM,
            "timeout_seconds": _PARAM,
            "auth": {
                "type": _PARAM,
                "cert_path": _PARAM,
                "key_path": _PARAM,
                "ca_cert_path": _PARAM,
                "token_env": _PARAM,
                "org_id": _PARAM,
            },
        },
    },
    build=_build,
)


__all__ = ["KaiExecutionContext", "KaiExecutionContextAdapter"]
