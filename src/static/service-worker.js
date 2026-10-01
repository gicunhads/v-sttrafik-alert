self.addEventListener("push", (event) => {
    let data = {
        title: "Trip Alert",
        body: "Your trip has an update.",
        url: "/trips"
    };

    if (event.data) {
        try {
            data = event.data.json();
        } catch (error) {
            console.error(
                "Could not parse push data:",
                error
            );
        }
    }

    const options = {
        body: data.body,
        data: {
            url: data.url || "/trips"
        }
    };

    event.waitUntil(
        self.registration.showNotification(
            data.title || "Trip Alert",
            options
        )
    );
});


self.addEventListener(
    "notificationclick",
    (event) => {

        event.notification.close();

        const url =
            event.notification.data?.url
            || "/trips";

        event.waitUntil(
            clients.openWindow(url)
        );
    }
);
