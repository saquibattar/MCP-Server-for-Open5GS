# MCP Server for Open5GS Core

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server that exposes selected Open5GS 5G Core management and monitoring operations as tools for MCP-compatible clients.

This GitHub repository contains the **MCP server only**. The Open5GS Docker deployment is maintained in a separate repository and must be cloned separately.

> [!WARNING]
> Use this project only in a lab environment you control. Never commit passwords, bearer tokens, subscriber authentication keys, or other secrets. The MCP server currently binds to `0.0.0.0:8000`, so it listens on all network interfaces. Restrict access with host/network firewall rules and do not expose it to untrusted networks.

## Table of contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [1. Clone both repositories](#1-clone-both-repositories)
- [2. Start the Open5GS lab](#2-start-the-open5gs-lab)
- [3. Set up and start the MCP server](#3-set-up-and-start-the-mcp-server)
- [4. Connect from Visual Studio Code](#4-connect-from-visual-studio-code)
- [5. Test with MCP Inspector](#5-test-with-mcp-inspector)
- [6. Verify the setup](#6-verify-the-setup)
- [7. Stop the environment](#7-stop-the-environment)
- [Configuration reference](#configuration-reference)
- [Troubleshooting](#troubleshooting)
- [Security notes](#security-notes)
- [Limitations](#limitations)

## Overview

The MCP server provides an interface for an MCP-compatible client to discover tools and invoke supported operations against the configured Open5GS environment.

The project includes tool groups for supported operations such as subscriber management, slice-related operations, QoS configuration, session monitoring, and other network-related utilities. The exact available tools depend on the current implementation in `mcp-server/src/`.

The server uses **Streamable HTTP** and is configured to listen on port `8000` on all interfaces (`0.0.0.0`). For a client running on the same machine, use:

```text
http://localhost:8000/mcp
```

Tool registration does not by itself prove that every operation has been exhaustively tested. Verify configuration changes and runtime network behaviour separately.

## Architecture

The setup consists of four main parts:

1. **MCP client** - Visual Studio Code with a compatible MCP extension, or MCP Inspector.
2. **MCP server** - This repository, which exposes tools over Streamable HTTP.
3. **Open5GS integration** - The integration mechanisms configured by the MCP server.
4. **Open5GS lab** - A separate Docker deployment containing the 5G Core and UERANSIM gNB/UE components.

The MCP client sends requests to the server. The server handles supported tool calls and returns results. The outcome depends on the tool invoked and the state and configuration of the Open5GS deployment.

## Prerequisites

Use a Linux environment for the commands below. Install:

- Git
- Docker Engine
- Docker Compose v2 (`docker compose`)
- Python 3 and `venv`
- Node.js and npm (only required for MCP Inspector)
- Sufficient disk space for the Docker images and containers

Check the installed tools:

```bash
git --version
docker --version
docker compose version
python3 --version
node --version
npm --version
```

The `node` and `npm` commands are only necessary if you plan to use MCP Inspector.

## 1. Clone both repositories

The MCP server and the Open5GS Docker deployment are separate Git repositories. The expected local layout is:

```text
~/MCP-Server-for-Open5GS/
├── docker_open5gs/             # Separate Open5GS Docker deployment
│   ├── sa-deploy.yaml
│   ├── nr-gnb.yaml
│   ├── nr-ue.yaml
│   └── ...
└── mcp-server/                 # This MCP server repository
    ├── docs/
    ├── src/
    ├── tests/
    ├── pyproject.toml
    ├── uv.lock
    └── README.md
```

### 1.1 Clone this MCP server repository

```bash
mkdir -p ~/MCP-Server-for-Open5GS
cd ~/MCP-Server-for-Open5GS

git clone https://github.com/FgfTk-FRA-UAS/MCP-Server-for-Open5GS.git mcp-server
```

If you have already cloned the repository, do not clone it again. Change into the existing directory and pull updates when appropriate.

### 1.2 Clone the separate Open5GS Docker repository

The Docker directory is **not included** in this MCP repository. The Compose filenames used by this setup correspond to the upstream [`herlesupreeth/docker_open5gs`](https://github.com/herlesupreeth/docker_open5gs) repository.

Clone it beside `mcp-server`:

```bash
cd ~/MCP-Server-for-Open5GS

git clone https://github.com/herlesupreeth/docker_open5gs.git docker_open5gs
```

The upstream repository may change over time. If the Compose files or configuration differ from the setup used by this project, check out the compatible revision used in your lab rather than assuming that the latest upstream revision is identical.

### 1.3 Check the directory layout

```bash
cd ~/MCP-Server-for-Open5GS

ls
ls docker_open5gs
ls mcp-server
```

Confirm that the Docker repository contains the Compose files used by the following steps:

```bash
cd ~/MCP-Server-for-Open5GS/docker_open5gs
ls -l sa-deploy.yaml nr-gnb.yaml nr-ue.yaml
```

If one or more files are missing, check that you cloned the correct repository and branch before continuing.

## 2. Start the Open5GS lab

Start the Open5GS Core first, then the simulated gNB, and finally the UE. Run these commands from the **Docker repository**, not from `mcp-server`.

```bash
cd ~/MCP-Server-for-Open5GS/docker_open5gs

docker compose -f sa-deploy.yaml up -d
docker compose -f nr-gnb.yaml up -d
docker compose -f nr-ue.yaml up -d
```

For the lab startup sequence used with this project, restart the gNB and UE after starting the Compose deployments:

```bash
docker restart nr_gnb
sleep 10
docker restart nr_ue
```

The container names above must match the names in your Docker deployment. If your Compose configuration uses different names, check them with `docker ps -a` and use the actual names.

### Check Docker status

```bash
docker ps
```

To inspect a container that failed to start:

```bash
docker logs --tail 100 <container_name>
```

Replace `<container_name>` with the name shown by Docker. A running container alone does not prove that the UE has registered or established a PDU session.

> **Important:** The Open5GS deployment may require configuration of its `.env` file, host IP address, PLMN, subscriber credentials, and Docker networking. Follow the upstream Docker repository instructions and the configuration used in your lab. Do not blindly replace an existing working configuration with example values.

## 3. Set up and start the MCP server

Open a **new terminal**. The MCP server runs from its own repository directory, separate from the Docker deployment.

```bash
cd ~/MCP-Server-for-Open5GS/mcp-server
```

### 3.1 Install the Python dependencies

This repository includes `pyproject.toml` and `uv.lock`. The recommended setup is to use `uv` to create the project environment and install the locked dependencies:

```bash
python3 -m pip install --user uv
uv sync
source .venv/bin/activate
```

Run these commands from the `mcp-server` directory. `uv sync` creates or updates the project virtual environment and installs the dependencies specified by the project files.

If your system's Python installation does not allow `pip install --user`, install `uv` using the method recommended for your operating system, then run `uv sync` and activate the environment.

Do not assume that a `requirements.txt` file exists; use the dependency files committed to the repository. Do not commit `.venv/`.

### 3.2 Configure environment variables

Set the variables in the same terminal where you will start the server:

```bash
export OPEN5GS_USERNAME='admin'
export OPEN5GS_PASSWORD='<YOUR_OPEN5GS_PASSWORD>'
export OPEN5GS_MCP_TOKEN='<YOUR_LONG_RANDOM_MCP_TOKEN>'
export PYTHONPATH="$(pwd)"
```

Replace the password and token placeholders with values for your own lab. The username `admin` is an example; use the username configured for your Open5GS management interface.

Generate a random MCP token locally:

```bash
openssl rand -hex 32
```

Set the generated value as `OPEN5GS_MCP_TOKEN`. You will need to provide the **same token** to the MCP client. The Open5GS management username/password and the MCP bearer token serve different purposes.

These `export` commands apply only to the current shell. If you open another terminal, set the variables there as well, or use an appropriately secured local environment configuration that is excluded from Git.

### 3.3 Start the MCP server

From the `mcp-server` directory, run:

```bash
python src/server.py
```

Keep this terminal open while using the MCP server. Although the local client endpoint is shown below, the server binds to all interfaces (`0.0.0.0:8000`), not only to localhost:

```text
http://localhost:8000/mcp
```

If the server exits with an error, check the terminal output and confirm that dependencies and required environment variables are configured.

## 4. Connect from Visual Studio Code

Use a Visual Studio Code MCP client/extension that supports HTTP MCP servers and input variables. Add the following configuration to the MCP configuration file expected by your installed client:

```json
{
  "servers": {
    "open5gs-mcp": {
      "type": "http",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer ${input:open5gs-mcp-token}"
      }
    }
  },
  "inputs": [
    {
      "type": "promptString",
      "id": "open5gs-mcp-token",
      "description": "Open5GS MCP bearer token",
      "password": true
    }
  ]
}
```

When prompted, enter the same value that you assigned to `OPEN5GS_MCP_TOKEN`.

The exact configuration location and UI depend on the MCP extension and VS Code version. If your extension expects a different configuration format, follow its documentation while preserving the server URL and bearer-token authentication required by your implementation.

### Connection checklist

1. Start the Open5GS Docker deployment.
2. Start the MCP server and keep its terminal running.
3. Load or reload the MCP connection in VS Code as required by your extension.
4. Enter the MCP bearer token when prompted.
5. Confirm that the client discovers the available tools.
6. Start with read-only tools before trying operations that change network state.

Tool discovery confirms that the client can communicate with the server; it does not guarantee that every tool can successfully complete its operation.

## 5. Test with MCP Inspector

MCP Inspector provides a separate way to connect to the server and inspect its tools. Keep the MCP server running and open another terminal:

```bash
cd ~/MCP-Server-for-Open5GS/mcp-server
npx @modelcontextprotocol/inspector@2.1.0
```

In MCP Inspector:

1. Select the connection option for an HTTP MCP server.
2. Set the URL to `http://localhost:8000/mcp`.
3. Configure the HTTP header `Authorization` with the value `Bearer <YOUR_LONG_RANDOM_MCP_TOKEN>`.
4. Use the same token configured as `OPEN5GS_MCP_TOKEN`.
5. Connect and inspect the available tools.
6. Test read-only operations first, then verify results before attempting state-changing operations.

If `npx` asks to download the package, review the prompt before proceeding. Do not include the bearer token in screenshots, source control, or public logs.

## 6. Verify the setup

Verify each layer separately.

### Docker deployment

```bash
docker ps
```

Confirm that the expected core, gNB, and UE containers are running. Inspect logs for components that fail or do not become ready.

### MCP server

Confirm that `python src/server.py` is still running without an unhandled exception and that the endpoint configured in the client is:

```text
http://localhost:8000/mcp
```

### MCP client

A successful connection should allow the client to discover the server's tools. Try a read-only tool and inspect its response.

### Open5GS operations and UE connectivity

For state-changing operations, inspect the tool result and use a corresponding read-back operation where available. Independently verify the actual Open5GS state, UE registration, PDU session state, and connectivity. These are distinct checks: a successful MCP response does not by itself prove end-to-end network connectivity.

## 7. Stop the environment

Stop the UE, gNB, and core deployments using the same Compose files:

```bash
cd ~/MCP-Server-for-Open5GS/docker_open5gs

docker compose -f nr-ue.yaml down
docker compose -f nr-gnb.yaml down
docker compose -f sa-deploy.yaml down
```

Stop the MCP server with `Ctrl+C` in its terminal. Stop MCP Inspector separately with `Ctrl+C` in its terminal.

The Compose `down` command removes the associated containers and Compose-managed networks. Persistent data depends on the volume configuration. Do **not** add `-v` unless you intentionally want to remove Compose-managed volumes and understand the data-loss implications.

## Configuration reference

| Setting | Purpose |
|---|---|
| `OPEN5GS_USERNAME` | Username for the configured Open5GS management interface |
| `OPEN5GS_PASSWORD` | Password for that management interface |
| `OPEN5GS_MCP_TOKEN` | Bearer token required by the MCP HTTP endpoint |
| `PYTHONPATH` | Set to the `mcp-server` project directory so Python can resolve project modules |
| MCP endpoint | `http://localhost:8000/mcp` |
| Transport | Streamable HTTP |
| MCP Inspector | `npx @modelcontextprotocol/inspector@2.1.0` |

The environment-variable names and behaviour must match the current server implementation. Update this section if the implementation changes.

## Troubleshooting

### A Compose file is missing

Make sure you are in the separate `docker_open5gs` directory:

```bash
cd ~/MCP-Server-for-Open5GS/docker_open5gs
ls -l sa-deploy.yaml nr-gnb.yaml nr-ue.yaml
```

If files are missing, check the repository URL, branch, and upstream deployment instructions.

### A container is not running

```bash
docker ps -a
docker logs --tail 100 <container_name>
```

Inspect the logs and configuration before repeatedly restarting containers. Image availability, ports, configuration files, networking, and host resources can all affect startup.

### The MCP server cannot authenticate to Open5GS

Check that `OPEN5GS_USERNAME` and `OPEN5GS_PASSWORD` match the credentials configured for the management interface. These credentials are separate from the MCP bearer token.

### The MCP client cannot connect

- Confirm that the MCP server process is still running.
- Confirm the URL is exactly `http://localhost:8000/mcp`.
- Confirm the request includes `Authorization: Bearer <token>`.
- Confirm that the token matches `OPEN5GS_MCP_TOKEN`.
- Check whether another process is already using the configured port.
- Review the MCP server terminal for errors.

### A tool returns an error

Check the MCP server terminal and the relevant Open5GS logs. Verify the tool parameters and whether the underlying Open5GS component is available. Tool discovery does not guarantee that the underlying operation will succeed.

### The UE does not register or a PDU session is missing

Check the gNB and UE container logs. Verify the lab's radio simulation, PLMN, subscriber configuration, DNN, slice, and network settings. A running container does not prove successful UE registration or data connectivity.

### MCP Inspector does not connect

Ensure the server is running, select an HTTP MCP connection, use the correct endpoint, and provide the correct bearer-token header. Inspector's UI may vary by version.

## Security notes

- Never commit real passwords, MCP tokens, Ki/OPc values, private keys, or other authentication secrets.
- Use a unique, sufficiently random MCP bearer token.
- Keep credentials in environment variables or an approved secret-management mechanism.
- Use a disposable test subscriber for destructive-operation tests.
- A confirmation parameter such as `confirm=true`, where supported, is a safeguard for destructive tools, not a substitute for authentication or authorization.
- The server binds to `0.0.0.0:8000`, which makes it listen on all network interfaces. Restrict access with firewall/network controls; do not expose it to untrusted networks without a security review.
- Redact sensitive subscriber information from public screenshots and logs.

## Limitations

- The server exposes a set of tools, but registration does not mean every tool has been exhaustively tested.
- Tool responses, configuration read-back, UE registration, PDU session state, and end-to-end connectivity are different forms of evidence and should be verified separately.
- Behaviour depends on the separately maintained Open5GS Docker deployment, its configuration, and the availability of its management interfaces.
- The Docker deployment is **not included** in this repository. Clone it separately from [`herlesupreeth/docker_open5gs`](https://github.com/herlesupreeth/docker_open5gs) and follow its instructions. The upstream repository can change, so use a compatible revision for reproducible results.

## Reporting issues

When reporting an issue, include the command, error message, affected component, and reproduction steps. Remove credentials, bearer tokens, subscriber authentication keys, and other sensitive information before sharing logs or screenshots.

---

**Project:** MCP Server for Open5GS Core  
**Author:** Saquib Attar  
**University:** Frankfurt University of Applied Sciences  
**Transport:** Streamable HTTP  
**MCP endpoint:** `http://localhost:8000/mcp`
