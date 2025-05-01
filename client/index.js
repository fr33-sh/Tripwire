function registerPushSubscription(oldSub, newSub) {
  fetch("/server/register-push-subscription", {
    method: "put",
    headers: {
      "Content-type": "application/json"
    },
    body: JSON.stringify({
      "old_sub": oldSub,
      "new_sub": newSub,
    })
  });
}


async function enablePush() {

  const perm = await Notification.requestPermission();
  if (perm === "denied") {
    throw "The user explicitly denied the permission request for notification.";
  }

  logBoth("The user granted the permission for notification.", console.info);

  // Get server's VAPID key.
  const vapidKeyResp = await fetch("/server/vapid-app-server-key");
  const vapidKey = await vapidKeyResp.text();
  console.info("Got server's VAPID key: ", vapidKey);

  // Subscribe to the push service,
  // unless already subscribed.
  const registration = await navigator.serviceWorker.getRegistration();
  const currentSub = await registration.pushManager.getSubscription();
  if (currentSub) {
    // TODO: Change UI if required.
    logBoth(
      "This client has already subscribed to the push service. The subscription " +
      "expiration time is: " + currentSub.expirationTime,
      console.info
    );

    registerPushSubscription(null, currentSub);

  } else {
    // Subscribe to the push service,
    const newSub = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidKey)
    });
    logBoth(
      "Subscribed to the push service successfully. The subscription " +
      "expiration time is: " + newSub.expirationTime,
      console.info
    )

    registerPushSubscription(null, newSub);
  }

  // TODO: Disable the enabling button.
}


async function disablePush() {
  // TODO: Implement.
  const registration = await navigator.serviceWorker.getRegistration();
  const subscription = await registration.pushManager.getSubscription();
}


function logOnPage(newLog) {
  logDiv = document.getElementById("log");
  currentLog = logDiv.innerHTML;
  logDiv.innerHTML = currentLog + "<br>" + newLog;
}


function logBoth(newLog, consoleLogFunc) {
  logOnPage(newLog);
  consoleLogFunc(newLog);
}


async function main() {

  console.info("Tripwire js started.");

  // Check browser support.
  if (!("serviceWorker" in navigator)) {
    throw "Service worker is not supported in this browser.";
  }
  if (!("PushManager" in window)) {
    throw "Push manager is not supported in this browser.";
  }

  // Register the sw.
  navigator.serviceWorker.register("sw.js")
  .then(function(registration) {
    console.info("sw.js is registered as a service worker.");
    return registration;
  }).catch(err => {
    console.error("Unable to register the service worker. Error: ", err);
  });

  // Request permission.
  // IOS requires user interaction before asking for permission.
  document.getElementById("enable-push").onclick = enablePush;
}

main();
