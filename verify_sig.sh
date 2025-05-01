#!/usr/bin/bash


openssl pkeyutl -verify -pubin -inkey instance/pubkey.pem -rawin -in "$2" -sigfile "$1"
