from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from src.tools.subscribers import (
    list_subscribers,
    get_subscriber,
    add_subscriber,
    update_subscriber,
    delete_subscriber
)

from src.tools.hateoas import (
    subscriber_links,
    slice_links,
    qos_links,
    network_links,
    ue_links,
    pdu_links
)

import json

from src.tools.sessions import (
    get_session_metrics,
    get_active_ues,
    get_pfcp_sessions,
    get_pfcp_peers
)

from src.tools.slices import (
    list_slices,
    add_slice,
    delete_slice,
    update_slice
)

from src.tools.qos import (
    get_qos,
    update_qos,
    get_slice_qos,
    update_slice_qos
)

from src.tools.analytics import (
    get_core_status,
    get_network_summary,
    get_subscriber_summary
)

from src.tools.health import (
    subscriber_exists,
    get_subscriber_health,
    get_network_health,
    get_subscriber_report
)

from src.tools.network_ops import (
    list_pdu_sessions,
    get_ue_status,
    get_slice_usage
)

import os
import secrets

from src.tools.ue_registration import (
    UEProfileError,
    build_ueransim_config,
    fetch_subscriber_profile,
)
from src.tools.ue_container_manager import (
    UEContainerError,
    create_managed_ue,
    stop_managed_ue,
)

from mcp.server.auth.provider import (
    AccessToken
)

from mcp.server.auth.settings import (
    AuthSettings
)


class SubscriberRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )


class DeleteSubscriberRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )
    confirm: bool = False


class SubscriberUpdateRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )
    subscriber: dict


class SliceRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )
    sst: int = Field(
        ge=1,
        le=255
    )


class AddSliceRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )
    slice: dict


class DeleteSliceRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )
    sst: int = Field(
        ge=1,
        le=255
    )
    confirm: bool = False


class UpdateSliceRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )
    sst: int = Field(
        ge=1,
        le=255
    )
    default_indicator: bool


class QoSRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )



class UpdateQoSRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )
    downlink: int = Field(ge=0)
    uplink: int = Field(ge=0)
    unit: int = Field(default=2, ge=0, le=4)
    five_qi: int | None = Field(default=None, ge=1, le=255)

    arp_priority_level: int | None = Field(
        default=None, ge=1, le=15
    )
    arp_pre_emption_capability: int | None = Field(
        default=None, ge=0, le=1
    )
    arp_pre_emption_vulnerability: int | None = Field(
        default=None, ge=0, le=1
    )



class UpdateSliceQoSRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )
    sst: int = Field(
        ge=1,
        le=255
    )
    downlink: int = Field(ge=0)
    uplink: int = Field(ge=0)
    unit: int = Field(
        default=2,
        ge=0,
        le=4
    )
    five_qi: int | None = Field(
        default=None,
        ge=1,
        le=255
    )



class SubscriberSummaryRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )


class SubscriberHealthRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )


class SubscriberReportRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )


class UEStatusRequest(BaseModel):
    imsi: str = Field(
        min_length=5,
        max_length=15,
        pattern=r"^\d+$"
    )


class SliceUsageRequest(BaseModel):
    sst: int = Field(
        ge=1,
        le=255
    )


class PDUSessionsRequest(BaseModel):
    dnn: str | None = None


class StaticTokenVerifier:

    async def verify_token(self, token: str):

        expected_token = os.environ.get(
            "OPEN5GS_MCP_TOKEN"
        )

        if not expected_token:
            return None

        if token != expected_token:
            return None

        return AccessToken(
            token=token,
            client_id="open5gs-copilot",
            scopes=["open5gs"]
        )


mcp = FastMCP(
    "Open5GS MCP Server",
    host="0.0.0.0",
    port=8000,
    streamable_http_path="/mcp",

    auth=AuthSettings(
        issuer_url="http://localhost:8000",
        resource_server_url=None,
        required_scopes=["open5gs"]
    ),

    token_verifier=StaticTokenVerifier()
)


# =====================================================
# Subscriber Management
# =====================================================

@mcp.tool(
    description="List all Open5GS subscribers."
)
def list_subscribers_tool():

    subscribers = json.loads(
        list_subscribers()
    )

    for subscriber in subscribers:

        security = subscriber.get("security")

        if security:
            subscriber["security"] = {
                "configured": True,
                "amf": security.get("amf")
            }

        imsi = subscriber.get(
            "imsi"
        )

        if imsi:

            subscriber["_links"] = (
                subscriber_links(
                    imsi
                )
            )

    return subscribers


@mcp.tool(
    description=(
        "Retrieve a subscriber's Open5GS profile by IMSI, including "
        "QoS and slice configuration. By default, authentication secrets "
        "are redacted. To include K (Ki) and OPc for an authorized lab "
        "test, set OPEN5GS_ALLOW_CREDENTIAL_READ=true in the server "
        "environment and restart the server."
    )
)
def get_subscriber_tool(request: SubscriberRequest):
    response = json.loads(get_subscriber(request.imsi))

    security = response.get("security")

    if security:
        allow_credentials = (
            os.environ.get("OPEN5GS_ALLOW_CREDENTIAL_READ", "false").lower()
            == "true"
        )

        if allow_credentials:
            # Return credentials only when explicitly enabled.
            response["security"] = {
                "configured": True,
                "amf": security.get("amf"),
                "k": security.get("k"),
                "opc": security.get("opc")
            }
        else:
            # Default behavior: redact authentication secrets.
            response["security"] = {
                "configured": True,
                "amf": security.get("amf")
            }

    response["_links"] = subscriber_links(request.imsi)

    return response




@mcp.tool(
    description=(
        "Create and provision a new Open5GS subscriber. "
        "Required input: imsi. Optional inputs: k (Ki), opc, sst, dnn, "
        "five_qi, session_ambr_downlink, session_ambr_uplink, ambr_unit, "
        "arp_priority_level, arp_pre_emption_capability, and "
        "arp_pre_emption_vulnerability. "
        "If k or opc is omitted, the server generates that value internally. "
        "K and OPc must be 32 hexadecimal characters when supplied. "
        "The subscriber is provisioned with the selected slice, DNN, "
        "session AMBR, 5QI and ARP."
    )
)
def add_subscriber_tool(
    imsi: str,
    k: str | None = None,
    opc: str | None = None,
    sst: int = 1,
    dnn: str = "internet",
    five_qi: int = 9,
    session_ambr_downlink: int = 1,
    session_ambr_uplink: int = 1,
    ambr_unit: int = 2,
    arp_priority_level: int = 8,
    arp_pre_emption_capability: int = 1,
    arp_pre_emption_vulnerability: int = 1,
):
    # Validate IMSI.
    if not imsi.isdigit() or not 5 <= len(imsi) <= 15:
        return {
            "success": False,
            "error": "IMSI must contain 5 to 15 digits."
        }

    if not 1 <= sst <= 255:
        return {
            "success": False,
            "error": "SST must be between 1 and 255."
        }

    if not dnn or not dnn.strip():
        return {
            "success": False,
            "error": "DNN must not be empty."
        }

    if not 1 <= five_qi <= 255:
        return {
            "success": False,
            "error": "5QI must be between 1 and 255."
        }

    if session_ambr_downlink < 0 or session_ambr_uplink < 0:
        return {
            "success": False,
            "error": "Session AMBR values cannot be negative."
        }

    if ambr_unit not in (0, 1, 2, 3, 4):
        return {
            "success": False,
            "error": "AMBR unit must be 0=bps, 1=Kbps, 2=Mbps, 3=Gbps, or 4=Tbps."
        }

    if not 1 <= arp_priority_level <= 15:
        return {
            "success": False,
            "error": "ARP priority level must be between 1 and 15."
        }

    if arp_pre_emption_capability not in (0, 1):
        return {
            "success": False,
            "error": "ARP pre-emption capability must be 0 or 1."
        }

    if arp_pre_emption_vulnerability not in (0, 1):
        return {
            "success": False,
            "error": "ARP pre-emption vulnerability must be 0 or 1."
        }

    # Check credentials supplied by the caller.
    import re

    for field_name, value in (("k", k), ("opc", opc)):
        if value is not None and not re.fullmatch(
            r"[0-9a-fA-F]{32}", value
        ):
            return {
                "success": False,
                "error": (
                    f"{field_name} must be exactly 32 hexadecimal characters "
                    "when supplied."
                )
            }

    # Avoid overwriting an existing subscriber.
    existing = subscriber_exists(imsi)

    if existing.get("exists"):
        return {
            "success": False,
            "imsi": imsi,
            "status": "already_exists",
            "message": "Subscriber already exists. No changes were made."
        }

    # Generate only the credential values that were not supplied.
    generated_k = k is None
    generated_opc = opc is None

    k = k if k is not None else secrets.token_hex(16)
    opc = opc if opc is not None else secrets.token_hex(16)

    subscriber = {
        "imsi": imsi,
        "security": {
            "amf": "8000",
            "k": k,
            "opc": opc
        },
        "ambr": {
            "downlink": {
                "value": 1,
                "unit": 3
            },
            "uplink": {
                "value": 1,
                "unit": 3
            }
        },
        "slice": [
            {
                "sst": sst,
                "default_indicator": True,
                "session": [
                    {
                        "name": dnn.strip(),
                        "type": 3,
                        "qos": {
                            "index": five_qi,
                            "arp": {
                                "priority_level": arp_priority_level,
                                "pre_emption_capability": (
                                    arp_pre_emption_capability
                                ),
                                "pre_emption_vulnerability": (
                                    arp_pre_emption_vulnerability
                                )
                            }
                        },
                        "ambr": {
                            "downlink": {
                                "value": session_ambr_downlink,
                                "unit": ambr_unit
                            },
                            "uplink": {
                                "value": session_ambr_uplink,
                                "unit": ambr_unit
                            }
                        },
                        "pcc_rule": []
                    }
                ]
            }
        ]
    }

    # Store the subscriber using the existing Open5GS integration.
    add_subscriber(subscriber)

    # Never return K or OPc in the creation response.
    return {
        "success": True,
        "imsi": imsi,
        "status": "provisioned",
        "authentication": "configured",
        "credential_source": {
            "k": "generated_internally" if generated_k else "caller_supplied",
            "opc": "generated_internally" if generated_opc else "caller_supplied"
        },
        "slice": {
            "sst": sst,
            "default": True
        },
        "dnn": dnn.strip(),
        "qos": {
            "five_qi": five_qi,
            "session_ambr": {
                "downlink": session_ambr_downlink,
                "uplink": session_ambr_uplink,
                "unit": ambr_unit
            },
            "arp": {
                "priority_level": arp_priority_level,
                "pre_emption_capability": arp_pre_emption_capability,
                "pre_emption_vulnerability": arp_pre_emption_vulnerability
            }
        },
        "message": (
            f"Subscriber {imsi} was provisioned. "
            "Authentication secrets were not included in this response."
        ),
        "_links": {
            "subscriber": {
                "tool": "get_subscriber_tool",
                "parameters": {"imsi": imsi}
            },
            "list_slices": {
                "tool": "list_slices_tool",
                "parameters": {"imsi": imsi}
            },
            "get_qos": {
                "tool": "get_qos_tool",
                "parameters": {"imsi": imsi}
            }
        }
    }



@mcp.tool(
    description=(
        "Update a subscriber's non-security configuration, such as supported "
        "subscription parameters. Authentication credentials K (Ki), OPc, "
        "OP and AMF are managed separately and cannot be changed through "
        "this tool."
    )
)
def update_subscriber_tool(request: SubscriberUpdateRequest):
    subscriber = request.subscriber

    if "security" in subscriber:
        return {
            "success": False,
            "imsi": request.imsi,
            "error": "Security credentials cannot be modified through this tool.",
            "message": "K, OPC, OP, and other authentication credentials are managed internally by the MCP server.",
            "_links": subscriber_links(request.imsi)
        }

    result = json.loads(
        update_subscriber(
            request.imsi,
            subscriber
        )
    )

    security = result.get("security")

    if security:
        result["security"] = {
            "configured": True,
            "amf": security.get("amf")
        }

    return {
        "result": result,
        "_links": subscriber_links(request.imsi)
    }

@mcp.tool(
    description=(
        "Permanently delete an Open5GS subscriber by IMSI. "
        "This is a destructive operation. "
        "Required fields: imsi and confirm. "
        "Never infer the IMSI. "
        "Do not execute unless confirm=true."
    )
)
def delete_subscriber_tool(request: DeleteSubscriberRequest):

    if not request.confirm:
        return {
            "confirmation_required": True,
            "imsi": request.imsi,
            "message": (
                f"Deleting subscriber {request.imsi} is a destructive operation. "
                "Set confirm=true to permanently delete it."
            )
        }

    result = delete_subscriber(
        request.imsi
    )

    return {
        "result": result,
        "_links": {
            "list_subscribers": {
                "tool": "list_subscribers_tool",
                "description": "List remaining subscribers."
            }
        }
    }


# =====================================================
# Slice Management
# =====================================================

@mcp.tool(
    description=(
        "List all network slices assigned to an Open5GS subscriber "
        "identified by IMSI."
    )
)
def list_slices_tool(request: SubscriberRequest):

    response = list_slices(
        request.imsi
    )

    for slice_item in response["slices"]:

        sst = slice_item.get("sst")

        if sst is not None:
            slice_item["_links"] = slice_links(
                request.imsi,
                sst
            )

    return response


@mcp.tool(
    description=(
        "Add a network slice to an Open5GS subscriber. "
        "Input format: {'imsi':'IMSI','slice':{...}}. "
        "The slice object must contain 'sst' and should contain "
        "'default_indicator' and 'session' when creating a "
        "fully configured slice. "
        "Each session should contain the DNN name, session type, "
        "QoS configuration, AMBR, and pcc_rule. "
        "For a slice that will later be configured with QoS, "
        "do not create the slice with an empty session list."
    )
)
def add_slice_tool(request: AddSliceRequest):

    result = add_slice(
        request.imsi,
        request.slice
    )

    sst = request.slice.get(
        "sst"
    )

    response = {
        "result": result
    }

    if sst is not None:

        response["_links"] = (
            slice_links(
                request.imsi,
                sst
            )
        )

    else:

        response["_links"] = {
            "subscriber": {
                "tool": "get_subscriber_tool",
                "parameters": {
                    "imsi": request.imsi,
                },
                "description": "Retrieve the subscriber."
            }
        }

    return response


@mcp.tool(
    description=(
        "Permanently delete a specific network slice from a specific "
        "Open5GS subscriber. This is a destructive operation. "
        "Required fields are imsi, sst, and confirm. "
        "Never infer the IMSI or SST. "
        "Do not execute unless confirm=true."
    )
)
def delete_slice_tool(request: DeleteSliceRequest):

    if not request.confirm:
        return {
            "confirmation_required": True,
            "imsi": request.imsi,
            "sst": request.sst,
            "message": (
                f"Deleting SST {request.sst} from subscriber "
                f"{request.imsi} is destructive. "
                "Set confirm=true to proceed."
            )
        }

    result = delete_slice(
        request.imsi,
        request.sst
    )

    return {
        "result": result,
        "_links": {
            "subscriber": {
                "tool": "get_subscriber_tool",
                "parameters": {
                    "imsi": request.imsi
                },
                "description": "Retrieve the subscriber."
            },
            "list_slices": {
                "tool": "list_slices_tool",
                "parameters": {
                    "imsi": request.imsi
                },
                "description": "List remaining slices."
            },
            "add_slice": {
                "tool": "add_slice_tool",
                "parameters": {
                    "imsi": request.imsi
                },
                "requires": [
                    "slice"
                ],
                "description": "Add a new slice."
            }
        }
    }


@mcp.tool(
    description="Update default slice indicator. Input format: {'imsi':'IMSI','sst':1,'default_indicator':true}"
)
def update_slice_tool(request: UpdateSliceRequest):

    result = update_slice(
        request.imsi,
        request.sst,
        request.default_indicator
    )

    return {
        "result": result,
        "_links": (
            slice_links(
                request.imsi,
                request.sst
            )
        )
    }


# =====================================================
# QoS Management
# =====================================================

@mcp.tool(
    description=(
        "Retrieve the dedicated QoS configuration for a subscriber. "
        "Use this tool when the user explicitly asks for subscriber QoS, "
        "AMBR, downlink rate, uplink rate, or QoS configuration. "
        "Input format: {'imsi':'001011234567895'}"
    )
)
def get_qos_tool(request: QoSRequest):

    response = get_qos(
        request.imsi
    )

    response["_links"] = (
        qos_links(
            request.imsi
        )
    )

    return response



@mcp.tool(
    description=(
        "Update subscriber session AMBR, optionally 5QI, and optionally ARP. "
        "ARP priority_level must be 1-15. "
        "pre_emption_capability and pre_emption_vulnerability must be 0 or 1. "
        "Omitted 5QI and ARP fields preserve their existing values. "
        "AMBR unit: 0=bps, 1=Kbps, 2=Mbps, 3=Gbps, 4=Tbps."
    )
)
def update_qos_tool(request: UpdateQoSRequest):

    result = update_qos(
        request.imsi,
        request.downlink,
        request.uplink,
        request.unit,
        request.five_qi,
        request.arp_priority_level,
        request.arp_pre_emption_capability,
        request.arp_pre_emption_vulnerability
    )

    return {
        "result": result,
        "_links": qos_links(
            request.imsi
        )
    }


@mcp.tool(
    description="Get QoS for a specific slice. Input format: {'imsi':'IMSI','sst':1}"
)
def get_slice_qos_tool(request: SliceRequest):

    response = get_slice_qos(
        request.imsi,
        request.sst
    )

    response["_links"] = (
        slice_links(
            request.imsi,
            request.sst
        )
    )

    return response


@mcp.tool(
    description=(
        "Update QoS for a specific network slice. "
        "AMBR unit: 0=bps, 1=Kbps, 2=Mbps, 3=Gbps, 4=Tbps. "
        "The default unit is Mbps (unit=2). "
        "Optionally specify five_qi (1-255); if omitted, "
        "the existing 5QI is preserved. "
        "Input format: "
        "{'imsi':'IMSI','sst':1,'downlink':20,'uplink':15,'unit':2,'five_qi':7}"
    )
)
def update_slice_qos_tool(request: UpdateSliceQoSRequest):

    result = update_slice_qos(
        request.imsi,
        request.sst,
        request.downlink,
        request.uplink,
        request.unit,
    request.five_qi
    )

    return {
        "result": result,
        "_links": (
            slice_links(
                request.imsi,
                request.sst
            )
        )
    }

# =====================================================
# Session Monitoring
# =====================================================

@mcp.tool(
    description=(
        "Retrieve current Open5GS session and connection metrics. "
        "Use this tool when the user asks for active UEs, active PFCP peers, "
        "active PFCP sessions, GTP2 sessions, or active bearers. "
        "Input: no parameters."
    )
)
def get_session_metrics_tool():

    response = get_session_metrics()

    response["_links"] = (
        network_links()
    )

    return response


@mcp.tool(
    description=(
        "Retrieve the current number of active Open5GS UEs. "
        "Use this tool when the user asks specifically for the active UE count. "
        "Input: no parameters."
    )
)
def get_active_ues_tool():

    response = get_active_ues()

    response["_links"] = (
        network_links()
    )

    return response


@mcp.tool(
    description=(
        "Retrieve the current number of active PFCP sessions in Open5GS. "
        "Use this tool when the user asks specifically for the PFCP session count. "
        "Input: no parameters."
    )
)
def get_pfcp_sessions_tool():

    response = get_pfcp_sessions()

    response["_links"] = (
        network_links()
    )

    return response


@mcp.tool(
    description=(
        "Retrieve the current number of connected PFCP peers in Open5GS. "
        "Use this tool when the user asks specifically for the PFCP peer count. "
        "Input: no parameters."
    )
)
def get_pfcp_peers_tool():

    response = get_pfcp_peers()

    response["_links"] = (
        network_links()
    )

    return response


# =====================================================
# Analytics
# =====================================================

@mcp.tool(
    description="Get Open5GS core status."
)
def get_core_status_tool():

    response = get_core_status()

    response["_links"] = (
        network_links()
    )

    return response


@mcp.tool(
    description="Get network summary including subscribers, UEs, PFCP sessions and slices."
)
def get_network_summary_tool():

    response = get_network_summary()

    response["_links"] = (
        network_links()
    )

    return response


@mcp.tool(
    description="Return a concise subscriber configuration summary including slice count, default slice, downlink QoS and uplink QoS. Input format: {'imsi':'001011234567895'}"
)
def get_subscriber_summary_tool(data: dict):

    response = get_subscriber_summary(
        data["imsi"]
    )

    response["_links"] = (
        subscriber_links(
            data["imsi"]
        )
    )

    return response

# =====================================================
# AI Friendly Operations
# =====================================================

@mcp.tool(
    description="Check whether a subscriber exists. Input format: {'imsi':'001011234567895'}"
)
def subscriber_exists_tool(request: SubscriberSummaryRequest):

    response = subscriber_exists(
        request.imsi
    )

    response["imsi"] = (
        request.imsi
    )

    if response["exists"]:

        response["_links"] = (
            subscriber_links(
                request.imsi
            )
        )

    else:

        response["_links"] = {
            "add_subscriber": {
                "tool": "add_subscriber_tool",
                "requires": [
                    "imsi"
                ],
                "description": (
                    "Create and provision a new subscriber. "
                    "Authentication credentials are generated and managed internally."
                )
            },
            "list_subscribers": {
                "tool": "list_subscribers_tool",
                "description": "List all subscribers."
            }
        }

    return response


@mcp.tool(
    description="Return subscriber health status including existence, QoS configuration status, default slice and overall subscriber health. Input format: {'imsi':'001011234567895'}"
)
def get_subscriber_health_tool(request: SubscriberHealthRequest):

    response = get_subscriber_health(
        request.imsi
    )

    response["_links"] = (
        subscriber_links(
            request.imsi
        )
    )

    return response


@mcp.tool(
    description="Get overall Open5GS network health."
)
def get_network_health_tool():

    response = get_network_health()

    response["_links"] = (
        network_links()
    )

    return response


@mcp.tool(
    description=(
        "Generate a detailed report for an Open5GS subscriber. "
        "Use this tool when the user asks for a detailed subscriber report, "
        "full subscriber report, comprehensive subscriber information, "
        "or a complete subscriber status report. "
        "The report includes subscriber configuration, device information, "
        "security configuration, subscriber AMBR, network slices, QoS, "
        "UE registration, PDU session status, and subscriber health. "
        "Do NOT use get_subscriber_tool when the user explicitly asks "
        "for a detailed report. "
        "Input format: {'imsi':'001011234567895'}"
    )
)
def get_subscriber_report_tool(request: SubscriberReportRequest):

    response = get_subscriber_report(
        request.imsi
    )

    security = response.get("security")

    if security:
        response["security"] = {
            "configured": True,
            "amf": security.get("amf")
        }

    response["_links"] = (
        subscriber_links(
            request.imsi
        )
    )

    return response


# =====================================================
# Advanced Session Operations
# =====================================================


@mcp.tool(
    description=(
        "List currently active PDU sessions in the Open5GS network, "
        "optionally filtered by DNN. Omit the request or DNN to list "
        "all active sessions. The output includes IMSI, DNN, UE IP "
        "address, slice information, and UPF anchor point when "
        "available from the live session data."
    )
)
def list_pdu_sessions_tool(request: PDUSessionsRequest | None = None):

    dnn = request.dnn if request is not None else None
    response = list_pdu_sessions(dnn)

    for session in response.get("sessions", []):
        imsi = session.get("imsi")

        if imsi:
            session["_links"] = pdu_links(imsi)

    return response



@mcp.tool(
    description="Return UE registration status and PDU session status for a subscriber. Input format: {'imsi':'001011234567895'}"
)
def get_ue_status_tool(request: UEStatusRequest):

    response = get_ue_status(
        request.imsi
    )

    response["_links"] = (
        ue_links(
            request.imsi
        )
    )

    return response


@mcp.tool(
    description="Return subscriber usage statistics for a network slice. Input format: {'sst':1}"
)
def get_slice_usage_tool(request: SliceUsageRequest):

    response = get_slice_usage(
        request.sst
    )

    response["_links"] = (
        network_links()
    )

    return response


# =====================================================
# Managed UERANSIM UE lifecycle
# =====================================================

@mcp.tool(
    description=(
        "Start a dedicated UERANSIM UE for an existing Open5GS subscriber. "
        "The subscriber profile is retrieved internally; authentication "
        "credentials and generated configuration are never returned."
    )
)
def start_managed_ue_tool(imsi: str):
    print(
        "[DEBUG start_managed_ue_tool]"
        f" type={type(imsi).__name__}"
        f" length={len(imsi) if isinstance(imsi, str) else 'n/a'}"
        f" ascii={imsi.isascii() if isinstance(imsi, str) else False}"
        f" digits={imsi.isdigit() if isinstance(imsi, str) else False}",
        flush=True,
    )
    if not isinstance(imsi, str) or not imsi.isdigit() or not 5 <= len(imsi) <= 15:
        return {
            "success": False,
            "error": "IMSI must contain 5 to 15 digits.",
        }

    try:
        profile = fetch_subscriber_profile(imsi)
        config = build_ueransim_config(
            imsi=imsi,
            profile=profile,
            gnb_ip="172.22.0.23",
            mcc="001",
            mnc="01",
            session_type_override=1,
        )
        return create_managed_ue(imsi, config)
    except (UEProfileError, UEContainerError) as exc:
        return {"success": False, "imsi": imsi, "error": str(exc)}
    except Exception:
        return {
            "success": False,
            "imsi": imsi,
            "error": "Unable to start the managed UE. No credentials were returned.",
        }



@mcp.tool(
    description=(
        "Stop and remove a UE container created by the managed UE tool. "
        "The container ownership labels must match the requested IMSI."
    )
)
def stop_managed_ue_tool(imsi: str):
    if not isinstance(imsi, str) or not imsi.isdigit() or not 5 <= len(imsi) <= 15:
        return {
            "success": False,
            "error": "IMSI must contain 5 to 15 digits.",
        }

    try:
        return stop_managed_ue(imsi)
    except UEContainerError as exc:
        return {"success": False, "imsi": imsi, "error": str(exc)}
    except Exception:
        return {
            "success": False,
            "imsi": imsi,
            "error": "Unable to stop the managed UE.",
        }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http"
    )
