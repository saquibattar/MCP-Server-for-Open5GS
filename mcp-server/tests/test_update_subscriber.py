from src.open5gs.rest_client import Open5GSClient


def main():
    client = Open5GSClient()
    client.login()

    updated_subscriber = {"subscriber_status": 1}

    print(
        client.update_subscriber(
            "001010000000999",
            updated_subscriber,
        )
    )


if __name__ == "__main__":
    main()
