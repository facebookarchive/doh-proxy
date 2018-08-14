# DNS Over HTTPS Proxy

[![Build Status](https://travis-ci.org/facebookexperimental/doh-proxy.svg?branch=master)](https://travis-ci.org/facebookexperimental/doh-proxy)
[![PyPI version](https://badge.fury.io/py/doh-proxy.svg)](https://badge.fury.io/py/doh-proxy)

A set of python 3 scripts that supports proxying DNS over HTTPS as specified
in the [IETF Draft draft-ietf-doh-dns-over-https](https://tools.ietf.org/html/draft-ietf-doh-dns-over-https-13).

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
$ doh-httpproxy \
    --upstream-resolver=::1 \
    --port 8080 \
    --listen-address ::1
```

`doh-httpproxy` now also supports TLS, that you can enable passing the 
args `--certfile` and `--keyfile` (just like `doh-proxy`)

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
# Also run flake8 on the testing files
$ flake8 test
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

## License
DOH Proxy is BSD-licensed.
