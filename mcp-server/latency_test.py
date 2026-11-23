import asyncio
import os
import statistics
import time

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


MCP_URL = "http://localhost:8000/mcp"
ITERATIONS = 10

TESTS = [
    {
        "name": "get_network_summary_tool",
        "arguments": {},
    },
    {
        "name": "get_subscriber_tool",
        "arguments": {
            "request": {
                "imsi": "001010000000001"
            }
        },
    },
    {
        "name": "list_pdu_sessions_tool",
        "arguments": {},
    },
    {
        "name": "get_session_metrics_tool",
        "arguments": {},
    },
    {
        "name": "get_subscriber_report_tool",
        "arguments": {
            "request": {
                "imsi": "001010000000001"
            }
        },
    },
]


async def main():
    token = os.environ.get("OPEN5GS_MCP_TOKEN")

    if not token:
        raise RuntimeError(
            "OPEN5GS_MCP_TOKEN environment variable is not set."
        )

    headers = {
        "Authorization": f"Bearer {token}"
    }

    async with streamablehttp_client(
        MCP_URL,
        headers=headers,
    ) as (
        read_stream,
        write_stream,
        _,
    ):

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            # Establish MCP session once.
            await session.initialize()

            print("=" * 70)
            print("MCP MULTI-TOOL LATENCY BENCHMARK")
            print("=" * 70)
            print(f"Server     : {MCP_URL}")
            print(f"Iterations : {ITERATIONS} per tool")
            print("=" * 70)

            results = {}

            for test in TESTS:

                tool_name = test["name"]
                arguments = test["arguments"]

                print()
                print("-" * 70)
                print(f"Testing: {tool_name}")
                print("-" * 70)

                timings = []

                for i in range(ITERATIONS):

                    start = time.perf_counter()

                    result = await session.call_tool(
                        tool_name,
                        arguments,
                    )

                    elapsed_ms = (
                        time.perf_counter() - start
                    ) * 1000

                    timings.append(elapsed_ms)

                    print(
                        f"Run {i + 1:2d}: "
                        f"{elapsed_ms:8.2f} ms"
                    )

                results[tool_name] = timings

                print()
                print(
                    f"Average : "
                    f"{statistics.mean(timings):.2f} ms"
                )
                print(
                    f"Median  : "
                    f"{statistics.median(timings):.2f} ms"
                )
                print(
                    f"Minimum : "
                    f"{min(timings):.2f} ms"
                )
                print(
                    f"Maximum : "
                    f"{max(timings):.2f} ms"
                )
                print(
                    f"Std Dev : "
                    f"{statistics.stdev(timings):.2f} ms"
                )

            print()
            print()
            print("=" * 90)
            print("FINAL LATENCY SUMMARY")
            print("=" * 90)

            print(
                f"{'Tool':<35}"
                f"{'Avg (ms)':>12}"
                f"{'Median':>12}"
                f"{'Min':>12}"
                f"{'Max':>12}"
                f"{'Std Dev':>12}"
            )

            print("-" * 90)

            for tool_name, timings in results.items():

                print(
                    f"{tool_name:<35}"
                    f"{statistics.mean(timings):>12.2f}"
                    f"{statistics.median(timings):>12.2f}"
                    f"{min(timings):>12.2f}"
                    f"{max(timings):>12.2f}"
                    f"{statistics.stdev(timings):>12.2f}"
                )

            print("=" * 90)


if __name__ == "__main__":
    asyncio.run(main())
