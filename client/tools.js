// This is from MDN's cookbook and then refactored.
function urlBase64ToUint8Array(b64) {
  var padding = '='.repeat((4 - b64.length % 4) % 4);
  var formattedB64 = (b64 + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  return base64ToUint8Array(formattedB64);
}

function base64ToUint8Array(b64) {
  var byteStr = window.atob(b64);
  return strToUint8Array(byteStr);
}

function strToUint8Array(str) {
  var outputArray = new Uint8Array(str.length);

  for (let i = 0; i < str.length; ++i) {
    outputArray[i] = str.charCodeAt(i);
  }
  return outputArray;
}

// Important for this to align with server's format
// so that signature verification won't break.
function timestampMsToDateTimeStr(timestampMs) {
  var dateTime = new Date(timestampMs);

  function pad(val) {
    return val >= 10 ? val.toString() : '0' + val.toString();
  }

  var dateTimeStr =
    dateTime.getFullYear() + '-' +
    // Month is 0-baesd...
    pad((dateTime.getMonth() + 1)) + '-' +
    pad(dateTime.getDate()) + ' ' +
    pad(dateTime.getHours()) + ':' +
    pad(dateTime.getMinutes()) + ':' +
    pad(dateTime.getSeconds());

  return dateTimeStr;
}

async function importPubKeyFromPEM(pem) {
  const pemHeader = '-----BEGIN PUBLIC KEY-----';
  const pemFooter = '-----END PUBLIC KEY-----';
  const b64 = pem.substring(
    pemHeader.length,
    pem.length - pemFooter.length - 1
  );

  const binaryDer = base64ToUint8Array(b64).buffer;

  return await window.crypto.subtle.importKey(
    'spki',
    binaryDer,
    {name: 'Ed25519'},
    true,
    ['verify'],
  );
}
