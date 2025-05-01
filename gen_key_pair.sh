#!/usr/bin/bash


echo "Generating ed25519 private key and saving at $1"
openssl genpkey -algorithm ED25519 -out "$1"
echo "Generating the public key and saving at $2"
openssl pkey -in "$1" -pubout -out "$2"
