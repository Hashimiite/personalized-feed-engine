import random

from locust import HttpUser, between, task


class FeedUser(HttpUser):
    wait_time = between(1, 3)  # users think between 1-3 seconds according to sample studies

    def on_start(self):
        """Assign each simulated user a random user_id (1-100)."""
        self.user_id = random.randint(1, 100)

    @task(3)
    def get_feed(self):
        """Fetch personalised feed - 3x more frequent than clicks."""
        self.client.get(f"/feed/{self.user_id}", name="/feed/[user_id]")

    @task(1)
    def click_post(self):
        """Simulate clicking a random post (assumes post ids 1-50 exist)."""
        post_id = random.randint(1, 50)
        self.client.post(f"/interact/{self.user_id}/{post_id}", name="/interact/[user_id]/[post_id]")
