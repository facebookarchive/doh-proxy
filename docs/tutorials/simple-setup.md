---
layout: default
---

In this examples, we will assume that we have the following setup:

* A digital certificate for `dns.example.com`
* cert file at `/etc/certs/dns.example.com/fullchain.pem`
* key file at `/etc/certs/dns.example.com/privkey.pem`
* a DNS resolver that listen on ::1 port 53.
* A `server` that will be running the `doh-proxy`, this is a host to which the traffic
will be sent encrypted and will perform the DNS request on our behalf.
In this example, the server is running at `fdbe:7d77:b04f:a2ca::1/64`
* A `client` that will run the `doh-stub`. We will configure our DNS queries to
be sent to the stub, which in turn will be proxied encrypted to our DOH server.

This document will focus on the `doh-proxy` tools arguments and where they
should be run. The specifics of configuring a DNS recursive resolver, reverse
proxy are outside the scope of this document and are already intensively
covered o the Internet.

# Simple setup

## Running the proxy

On the `server`, we run the `doh-proxy` as root:

```shell
$ sudo doh-proxy \
    --certfile /etc/certs/dns.example.com/fullchain.pem \
    --keyfile /etc/certs/dns.example.com/privkey.pem \
    --upstream-resolver ::1
```

## Running the client stub

On the `client`
```shell
$ sudo doh-stub \
    --domain dns.example.com \
    --remote-address fdbe:7d77:b04f:a2ca::1 \
     --listen-address ::1
```

You can test it by running a `dig` on the `client`:
```shell
$ dig @::1 example.com
```

To start using it, update `/etc/resolv.conf` and change `nameserver` do be:
```
nameserver ::1
```



