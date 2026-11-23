from src.open5gs.rest_client import Open5GSClient

client = Open5GSClient()

client.login()

print(client.get_subscriber("001010000000001"))
