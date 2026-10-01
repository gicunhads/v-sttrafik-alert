import base64
import json
import os
import tempfile

from pywebpush import (
    webpush,
    WebPushException
)

from database import (
    get_push_subscriptions,
    delete_push_subscription
)


def get_vapid_private_key():
    encoded_key = os.getenv(
        "VAPID_PRIVATE_KEY_BASE64"
    )

    if encoded_key:
        try:
            private_key = base64.b64decode(
                encoded_key
            )
        except Exception as error:
            raise ValueError(
                "VAPID_PRIVATE_KEY_BASE64 "
                "is invalid."
            ) from error

        key_path = os.path.join(
            tempfile.gettempdir(),
            "vapid_private.pem"
        )

        with open(
            key_path,
            "wb"
        ) as key_file:
            key_file.write(
                private_key
            )

        return key_path

    # Local development fallback.
    local_key_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "vapid_private.pem"
        )
    )

    if os.path.exists(
        local_key_path
    ):
        return local_key_path

    raise ValueError(
        "No VAPID private key is configured."
    )


VAPID_PRIVATE_KEY = (
    get_vapid_private_key()
)


def send_push_to_user(
    user_id,
    title,
    message
):
    subscriptions = (
        get_push_subscriptions(
            user_id
        )
    )

    if not subscriptions:
        print(
            f"No push subscriptions "
            f"for user {user_id}"
        )
        return 0

    payload = json.dumps({
        "title": title,
        "body": message,
        "url": "/trips"
    })

    successful_pushes = 0

    for subscription in subscriptions:

        subscription_info = {
            "endpoint":
                subscription["endpoint"],

            "keys": {
                "p256dh":
                    subscription["p256dh"],

                "auth":
                    subscription["auth"]
            }
        }

        try:
            webpush(
                subscription_info=
                    subscription_info,

                data=payload,

                vapid_private_key=
                    VAPID_PRIVATE_KEY,

                vapid_claims={
                    "sub":
                        "mailto:trip-alert@example.com"
                },

                ttl=300
            )

            successful_pushes += 1

            print(
                f"Push sent to user "
                f"{user_id}"
            )

        except WebPushException as error:

            print(
                "Push notification failed:",
                error
            )

            if (
                error.response is not None
                and
                error.response.status_code
                in (404, 410)
            ):
                delete_push_subscription(
                    subscription["endpoint"]
                )

    return successful_pushes
