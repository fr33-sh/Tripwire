self.addEventListener("push", (event) => {

  // Keep the service worker alive until the notification is created.
  event.waitUntil(
    self.registration.showNotification("Test title", {
      body: event.data.text()
    })
  );
});


// Handle push subscription expiration by resubscribing to the push service
// and then re-registering with the app server.
// MDN's example resubscribes while Pushpad does not, and just
// re-registers using `event.newSubscription`.
//
// Which one is correct?
// TODO: Test the handler upon expiration!
//
// https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerGlobalScope/pushsubscriptionchange_event
// https://pushpad.xyz/service-worker.js
//
self.addEventListener(
  "pushsubscriptionchange",
  (event) => {
    logBoth(
      "The push subscription probably expired because the client received " +
      "a \"pushsubscriptionchange\" event: " + event + "Because this event does " +
      "not happen often, its handler is *not* sufficiently tested!",
      console.warn
    );

    const subscription = self.registration.pushManager
      .subscribe(event.oldSubscription.options)
      .then((newSubscription) =>
        registerPushSubscription(
          event.oldSubscription,
          newSubscription
        )
      );

    event.waitUntil(subscription);
  },
  false,
);
