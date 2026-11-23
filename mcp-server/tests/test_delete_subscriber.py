from src.open5gs.rest_client import Open5GSClient


def main():
    client = Open5GSClient()
    client.login()
    print(client.delete_subscriber("001010000000999"))


if __name__ == "__main__":
    main()
