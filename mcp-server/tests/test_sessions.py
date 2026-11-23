from src.tools.sessions import (
    get_session_metrics,
    get_active_ues,
    get_pfcp_sessions,
    get_pfcp_peers
)

print(get_session_metrics())
print(get_active_ues())
print(get_pfcp_sessions())
print(get_pfcp_peers())
