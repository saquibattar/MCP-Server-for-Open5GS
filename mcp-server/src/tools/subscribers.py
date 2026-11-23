from src.open5gs.rest_client import Open5GSClient


def list_subscribers():
    client = Open5GSClient()
    client.login()
    return client.list_subscribers()


def get_subscriber(imsi):
    client = Open5GSClient()
    client.login()
    return client.get_subscriber(imsi)


def add_subscriber(subscriber):
    client = Open5GSClient()
    client.login()

    if "subscriber" in subscriber:
        subscriber = subscriber["subscriber"]

    return client.add_subscriber(subscriber)


def update_subscriber(imsi, subscriber):
    client = Open5GSClient()
    client.login()

    if "subscriber" in subscriber:
        subscriber = subscriber["subscriber"]

    return client.update_subscriber(
        imsi,
        subscriber
    )


def delete_subscriber(imsi):
    client = Open5GSClient()
    client.login()
    return client.delete_subscriber(imsi)
