from pymongo import MongoClient


class MongoDBClient:

    def __init__(self):

        self.client = MongoClient(
            "mongodb://172.22.0.2:27017/"
        )

        self.db = self.client["open5gs"]

        self.subscribers = self.db["subscribers"]

    def list_subscribers(self):

        return list(
            self.subscribers.find(
                {},
                {"_id": 0}
            )
        )

    def get_subscriber(self, imsi):

        return self.subscribers.find_one(
            {"imsi": imsi},
            {"_id": 0}
        )

    def subscriber_exists(self, imsi):

        subscriber = self.subscribers.find_one(
            {"imsi": imsi}
        )

        return subscriber is not None

    def count_subscribers(self):

        return self.subscribers.count_documents(
            {}
        )

    def count_slice_usage(self, sst):

        count = 0

        subscribers = self.subscribers.find(
            {},
            {
                "_id": 0,
                "slice.sst": 1
            }
        )

        for subscriber in subscribers:

            for slice_item in subscriber.get(
                "slice",
                []
            ):

                if (
                    slice_item.get("sst")
                    == sst
                ):
                    count += 1

        return count

    def count_total_slices(self):

        total = 0

        subscribers = self.subscribers.find(
            {},
            {
                "_id": 0,
                "slice": 1
            }
        )

        for subscriber in subscribers:

            total += len(
                subscriber.get(
                    "slice",
                    []
                )
            )

        return total

    def get_default_sst(self, imsi):

        subscriber = self.subscribers.find_one(
            {"imsi": imsi},
            {
                "_id": 0,
                "slice": 1
            }
        )

        if not subscriber:
            return None

        for slice_item in subscriber.get(
            "slice",
            []
        ):

            if slice_item.get(
                "default_indicator",
                False
            ):
                return slice_item.get(
                    "sst"
                )

        if subscriber.get("slice"):

            return subscriber[
                "slice"
            ][0].get(
                "sst"
            )

        return None
