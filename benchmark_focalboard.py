import json
import logging
import time
from src.focalboard.focalboard_client import FocalboardClient
from src.db.db_client import DBClient

logging.basicConfig(level=logging.WARNING)


def measure_time(func, *args, **kwargs):
    start = time.time()
    result = func(*args, **kwargs)
    end = time.time()
    return result, end - start


with open("config.json", "r") as f:
    config = json.load(f)

if "board_id" not in config["focalboard"]:
    config["focalboard"]["board_id"] = "dummy_board_id"

# Need a configured DBClient for get_boards_for_telegram_user
db_client = DBClient(config["db"])
client = FocalboardClient(config["focalboard"])


# Mock the network requests to simulate 50ms latency
def mock_make_request(uri, payload={}):
    time.sleep(0.05)  # 50ms network latency
    if "api/v2/users/" in uri:
        # Mocking individual user fetch
        return 200, {"id": uri.split("/")[-1], "username": "mock_user"}
    elif "api/v2/users" in uri:
        # Mocking bulk user fetch
        return 200, [
            {"id": f"user_{i}", "username": f"mock_user_{i}"} for i in range(30)
        ]
    elif "boards" in uri and "members" in uri:
        # Mocking board members fetch
        return 200, [{"userId": f"user_{i}"} for i in range(30)]
    elif "api/v2/teams/0/boards" in uri:
        # Mocking boards fetch
        return 200, [{"id": f"board_{i}", "title": f"Board {i}"} for i in range(10)]
    return 200, []


client._make_request = mock_make_request


# Test 1: Just the prefetch execution (new logic)
client._users_cache = {}
print("--- Testing new _prefetch_all_users() ---")
_, duration1 = measure_time(client._prefetch_all_users)
print(f"Time to prefetch all users: {duration1:.4f} seconds")
print(f"Users cached: {len(client._users_cache)}")

# Clear the cache to test again
client._users_cache = {}

print("\n--- Testing get_boards_for_telegram_user (simulating full run) ---")
# Pick a random user to test on that we know should have boards, maybe the one running the bot
# houndlord is probably the dev, let's try get_boards_for_user directly
# Actually, FocalboardClient.get_boards_for_user() fetches all boards, then members
print("Fetching boards and their members...")

start_boards = time.time()
try:
    # We mock get_boards_for_user because db_client is not fully mocked, let's just test get_members for 10 boards manually
    for i in range(10):
        client.get_members(f"board_{i}")
    end_boards = time.time()
    print(
        f"Time to fetch members for 10 boards (with prefetch): {end_boards - start_boards:.4f} seconds"
    )
except Exception as e:
    print(f"Error occurred during boards fetch: {e}")

# Test 3: Simulating the old N+1 way (without prefetch)
print("\n--- Testing legacy N+1 get_members ---")
client._users_cache = {}  # Ensure cache is empty
# Hack _prefetch_all_users to do nothing for this test
original_prefetch = client._prefetch_all_users
client._prefetch_all_users = lambda: None

start_legacy = time.time()
try:
    for i in range(10):
        client.get_members(f"board_{i}")
    end_legacy = time.time()
    print(
        f"Time to fetch members for 10 boards (N+1 old method): {end_legacy - start_legacy:.4f} seconds"
    )
    print(
        f"Speedup multiplier: {(end_legacy - start_legacy) / (end_boards - start_boards):.1f}x faster!"
    )
except Exception as e:
    print(f"Error occurred during boards fetch: {e}")
finally:
    client._prefetch_all_users = original_prefetch
