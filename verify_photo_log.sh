#!/usr/bin/bash
set -ue -o pipefail

if [ $# -ne 2 ]; then
  echo "
    You need to provide the public key file as the first argument,
    and the photo log directory as the second argument.
  "
  exit
fi

pubkey_path="$1"
captures_dir="$2"
tmp_dir='/tmp/tripwire/'

# Colored output
RED='\033[0;31m'
NO_COLOR='\033[0m'

if [ -d "$tmp_dir" ]; then
  echo "Trying to create ${tmp_dir} but it already exists. Check its content and remove it first."
  exit
fi
mkdir "$tmp_dir"

photo_count=$(ls -1q ${captures_dir}*.jpg | wc -l)
good_sig_count=0
for photo_path in ${captures_dir}*.jpg; do
  datetime=$(basename "${photo_path%.*}")
  sig_path="${captures_dir}${datetime}.sig"

  photo_hash=$(shasum -a 256 "$photo_path" | cut -d ' ' -f 1)

  str="${datetime},${photo_hash}"
  str_path="${tmp_dir}str.txt"
  echo -n "$str" > "$str_path"

  # If no signature for a photo
  if [ ! -f "$sig_path" ]; then
    echo -e "${RED}
      There is no signature for \"${photo_path}\".
      If there has been a network outage and secrets cannot be remotely compared,
      and if this time is before when you entered the deployment area, then Tripwire
      has probably detected intrusion! Check the few (signed) photos before this time
      to see whether the detection was a true or false positive.

      Aborted.
    ${NO_COLOR}"
    break
  fi

  # Verify the signature.
  if openssl pkeyutl -verify -pubin -inkey "$pubkey_path" -rawin -in "$str_path" \
    -sigfile "$sig_path" > /dev/null;
  then
    echo "Good signature for ${photo_path}"
    good_sig_count=$((good_sig_count + 1))
  else
    echo -e "${RED}
      Bad signature for \"${photo_path}\"!
      The photo log has probably been tampered with!

      Aborted.
    ${NO_COLOR}"
    break
  fi
done

echo "Verified ${good_sig_count} good signatures."
echo "There are ${photo_count} photos in total."

rm -rf "$tmp_dir"
