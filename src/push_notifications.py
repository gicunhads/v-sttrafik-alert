import json
import os

from pywebpush import (
    webpush,
    WebPushException
)

from database import (
    get_push_subscriptions,
    delete_push_subscription
)


VAPID_PRIVATE_KEY = os.path.join(
    os.path.dirname(__file__),
    "..",
    "vapid_private.pem"
)


def send_push_to_user(
    user_id,
    title,
    message
):
    subscriptions = get_push_subscriptions(
        user_id
    )

    if not subscriptions:
        print(
            f"No push subscriptions for user {user_id}"
        )
        return

    payload = json.dumps({
        "title": title,
        "body": message,
        "url": "/trips"
    })

    for subscription in subscriptions:

        subscription_info = {
            "endpoint": subscription["endpoint"],

            "keys": {
                "p256dh": subscription["p256dh"],
                "auth": subscription["auth"]
            }
        }

        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": "mailto:trip-alert@example.com"
                },
                ttl=300
            )

            print(
                f"Push sent to user {user_id}"
            )

        except WebPushException as error:

            print(
                "Push notification failed:",
                error
            )

            if (
                error.response is not None
                and error.response.status_code
                in (404, 410)
            ):
                delete_push_subscription(
                    subscription["endpoint"]
                )
