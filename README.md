# DNS Over HTTPS Proxy

[![Build Status](https://travis-ci.org/facebookexperimental/doh-proxy.svg?branch=master)](https://travis-ci.org/facebookexperimental/doh-proxy)
[![PyPI version](https://badge.fury.io/py/doh-proxy.svg)](https://badge.fury.io/py/doh-proxy)

A set of python 3 scripts that supports proxying DNS over HTTPS as specified
in the [IETF Draft draft-ietf-doh-dns-over-https](https://tools.ietf.org/html/draft-ietf-doh-dns-over-https-03).

DOH provides a way to run encrypted DNS over HTTPS, a protocol which can freely
traverse firewalls when other encrypted mechanism may be blocked.

The project comes with a set of 4 tools:

* [doh-proxy](#doh-proxy): A service that receives DOH queries over HTTP2 and forwards them
to a recursive resolver.
* [doh-httpproxy](#doh-httpproxy): Like `doh-proxy` but uses HTTP instead of HTTP2.
The main intent is to run this behind a reverse proxy.
* [doh-stub](#doh-stub): A service that listens for DNS queries and forwards them to a DOH server.
* [doh-client](#doh-client): A tool to perform a test DNS query against DOH server.

See the `CONTRIBUTING` file for how to help out.

DOH Proxy was created during [IETF Hackathon 100](https://www.ietf.org/how/runningcode/hackathons/100-hackathon/) as a proof-of-concept and is not used at Facebook.

You are welcome to use it, but be aware that support is limited and best-effort.

## Installing

To install an already packaged version directly from PyPi:

```shell
$ pip3 install doh-proxy
```

## Usage

### doh-proxy

`doh-proxy` is a stand alone server answering DOH request. The proxy does not do
DNS recursion itself and rather forward the query to a full-featured DNS
recursive server or DNS caching server.

By running `doh-proxy`, you can get and end-to-end DOH solution with minimal
setup.

```shell
$ sudo doh-proxy \
    --upstream-resolver=::1 \
    --certfile=./fullchain.pem \
    --keyfile=./privkey.pem
```

### doh-httpproxy

`doh-httpproxy` is designed to be running behind a reverse proxy. In this setup
a reverse proxy such as [NGINX](https://nginx.org/) would be handling the
HTTPS/HTTP2 requests from the DOH clients and will forward them to
`doh-httpproxy` backends.

While this setup requires more upfront setup, it allows running DOH proxy
unprivileged and on multiple cores.


```shell
$ sudo doh-httpproxy \
    --upstream-resolver=::1 \
    --port 8080 \
    --listen-address ::1
```


### doh-stub

`doh-stub` is the piece of software that you would run on the clients. By
providing a local DNS server, `doh-stub` will forward the DNS requests it
receives to a DOH server using an encrypted link.

You can start a stub resolver with:

```shell
$ doh-stub \
    --listen-port 5553 \
    --listen-address ::1 \
    --domain foo.bar \
    --remote-address ::1
```

and query it.

```shell
$ dig @::1 -p 5553 example.com
```

### doh-client

`doh-client` is just a test cli that can be used to quickly send a request to
a DOH server and dump the returned answer.

```shell
$ doh-client  \
    --domain dns.dnsoverhttps.net \
    --qname sigfail.verteiltesysteme.net \
    --dnssec
id 37762
opcode QUERY
rcode SERVFAIL
flags QR RD RA
edns 0
eflags DO
payload 4096
;QUESTION
sigfail.verteiltesysteme.net. IN AAAA
;ANSWER
;AUTHORITY
;ADDITIONAL

$ doh-client  \
    --domain dns.dnsoverhttps.net \
    --qname sigok.verteiltesysteme.net \
    --dnssec
id 49772
opcode QUERY
rcode NOERROR
flags QR RD RA AD
edns 0
eflags DO
payload 4096
;QUESTION
sigok.verteiltesysteme.net. IN AAAA
;ANSWER
sigok.verteiltesysteme.net. 60 IN AAAA 2001:638:501:8efc::139
sigok.verteiltesysteme.net. 60 IN RRSIG AAAA 5 3 60 20180130030002 20171031030002 30665 verteiltesysteme.net. O7QgNZFBu3fULvBXwM39apv5nMehh51f mLOVEsC8qZUyxIbxo4eDLQt0JvPoPpFH 5TbWdlm/jxq5x2/Kjw7yUdpohhiNmdoD Op7Y+RyHbf676FoC5Zko9uOAB7Pp8ERz qiT0QPt1ec12bM0XKQigfp+2Hy9wUuSN QmAzXS2s75k=
;AUTHORITY
;ADDITIONAL
```

## Development


### Requirements

* python >= 3.5
* aiohttp
* aioh2
* dnspython

### Building

DOH Proxy uses Python'setuptools to manage dependencies and build.

To install its dependencies:

```shell
$ python3 setup.py develop
```

To build:
```shell
$ python3 setup.py build
```

To run unittests:
```shell
$ python3 setup.py test
```

To run the linter:
```shell
$ python3 setup.py flake8
```

From within the root of the repository, you can test the proxy, stub and client respectively
by using the following commands:

```shell
$ sudo PYTHONPATH=. ./dohproxy/proxy.py ...
```

```shell
$ PYTHONPATH=. ./dohproxy/httpproxy.py ...
```


```shell
$ PYTHONPATH=. ./dohproxy/stub.py ...
```

```shell
$ PYTHONPATH=. ./dohproxy/client.py ...
```

## Example setups

In those examples, we will assume that we have the following setup:

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

### Simple setup

On the `server`, we run the `doh-proxy` as root:

```shell
$ sudo doh-proxy \
    --certfile /etc/certs/dns.example.com/fullchain.pem \
    --keyfile /etc/certs/dns.example.com/privkey.pem \
    --upstream-resolver ::1
```

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
### Behind a reverse proxy

In this setup, we will run a reverse proxy server that will take care of
handling https request and forward them to a `dns-httpproxy` that runs on the
same host.


Assuming we use [nginx](https://nginx.org/) as our reverse proxy and 2 instances
of `doh-httpproxy`, one listening on port 8080 and the other one on port 8081.


To run the `doh-httpproxy` processes:

```shell
$ doh-httpproxy --upstream-resolver ::1 --port 8080 --listen-address=::1
$ doh-httpproxy --upstream-resolver ::1 --port 8081 --listen-address=::1
```

Also see how to  [run `doh-httpproxy` under `systemd`](#running-doh-httpproxy-under-systemd)

And then the relevant Nginx config would look like:

```
upstream backend {
        server [::1]:8080;
        server [::1]:8081;
}

server {
        listen 443 ssl http2 default_server;
        listen [::]:443 ssl http2 default_server;

        server_name dns.example.com;

        location / {
              proxy_set_header Host $http_host;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              proxy_redirect off;
              proxy_buffering off;
              proxy_pass http://backend;
        }

        ssl_prefer_server_ciphers on;
        ssl_ciphers EECDH+CHACHA20:EECDH+AES128:RSA+AES128:EECDH+AES256:RSA+AES256:EECDH+3DES:RSA+3DES:!MD5;

        ssl_certificate /etc/certs/dns.example.com/fullchain.pem;
        ssl_certificate_key /etc/certs/dns.example.com/privkey.pem;
        ssl_dhparam /etc/nginx/ssl/dhparam.pem;
}
```

### Running doh-httpproxy under systemd

#### Create a dedicated user
```bash
adduser -r doh-proxy \
    -d /var/lib/doh-proxy \
    -c 'DOH Proxy server' \
    -s /sbin/nologin \
    -U
mkdir /var/lib/doh-proxy \
    && chown doh-proxy: /var/lib/doh-proxy \
    && chown 700 /var/lib/doh-proxy
```

#### Create a `doh-httpproxy` unit file

```bash
cat <<EOF > /etc/systemd/system/doh-httpproxy\@.service
[Unit]
Description=DOH HTTP Proxy on %I
After=syslog.target network.target
Before=nginx.target

[Service]
Type=simple
ExecStart=/bin/doh-httpproxy --upstream-resolver ::1 --level DEBUG --listen-address=127.0.0.1 --port %I
Restart=always
User=doh-proxy
Group=doh-proxy

[Install]
WantedBy=multi-user.target
EOF

systemctl reload-daemon
```

#### Set symlinks for each ports you want doh-httpproxy to run on run it

```bash
for i in 8080 8081
do
    ln -s /etc/systemd/system/doh-httpproxy\@.service \
        /etc/systemd/system/doh-httpproxy\@${i}.service
    systemctl start doh-httpproxy@${i}
done
```


The client side is identical to the [simple setup](#simple-setup)

## License
DOH Proxy is BSD-licensed.
