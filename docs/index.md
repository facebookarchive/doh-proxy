---
layout: default
---
# DNS Over HTTPS Proxy

![Test Code Base](https://github.com/facebookexperimental/doh-proxy/workflows/Test%20Code%20Base/badge.svg)
[![GitHub Super-Linter](https://github.com/facebookexperimental/doh-proxy/workflows/Lint%20Code%20Base/badge.svg)](https://github.com/marketplace/actions/super-linter)
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
# Due to GH #63
$ pip install git+https://github.com/URenko/aioh2#egg=aioh2
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

DOH Proxy uses GitHub Action [Super-Linter](https://github.com/marketplace/actions/super-linter) to lint the code. In order to validate your code locally, it is possible to run Super-Linter locally using the following comand line from within the repository:

```shell
docker run -e RUN_LOCAL=true  -e VALIDATE_PYTHON_PYLINT=false \
    -e FILTER_REGX_INCLUDE='(dohproxy|test)/.*.py' \
    -v $(pwd):/tmp/lint \
     --rm github/super-linter:v3
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
## Tutorials

Check the [tutorial page](tutorials.md)
# Changelog

## [Unreleased]

### Fixed
- fix unittests pattern matching. GH #78
- force aiohttp < 4.0.0. GH #78
- close transport on Timeout. GH #79
- don't decode body twice. GH #83 @tiran
- handle get\_extra\_info('peername') being None. GH #89
- add legal link to web site. GH #90
- define flake8 defaults. GH #91 @rfinnie
- set `Accept` header in client queries. GH #95

### Changes
- improve logging. GH #87
- support multiple --listen-address. GH 85 @rfinnie
- Add support for ECS. GH #88 @rfinnie

## [0.0.9] - 2019-07-04

### Fixed
- fix copyright headers. GH #51
- fix flake8 error
- loglevel (--level) was ignore in DNSClient. GH #58
- Do not set_result when coroutine is already cancelled. GH #59
- Remove NPN support. GH #64
- Properly close UDP transport after an exception occured. GH #66

## [0.0.8] - 2018-08-14

### Changes
- [doc] don't use `sudo` when not required. @jpmens
- version bump to get markdown rendering on pypi.

## [0.0.7] - 2018-08-13

### Fixed
- Handle dns message with empty question section GH #21
- Make https://pypi.org/project/doh-proxy/ display description using markdown syntax.

### Changes
- separate server side protocol classes from client side ones
- Support for [draft-13](https://tools.ietf.org/html/draft-ietf-doh-dns-over-https-13). @bagder
- DNSClientProtocol is now an async friendly class which will retry over TCP on timeout and/or TC bit set. @newEZ
- Both `doh-httpproxy` and `doh-proxy` now use the new DNSClient @newEZ and @chantra

### Added
- support listening from multiple IPs for proxy services.
- Added support for TLS in `doh-httpproxy` @lucasvasconcelos
- Pass optional `cafile` to `doh-stub` to be able to connect to service using custom CA @fim

## [0.0.6] - 2018-02-20

### Added
- custom upstream port option GH #16
- display version with --version

### Fixed
- set :scheme pseudo-header correctly.  GH #17

## [0.0.5] - 2018-02-05

### Added
- Unittest coverage of httpproxy.py

### Changes
- @jedisct1 change DOH_BODY_PARAM to `dns` to match draft-ietf-doh-dns-over-https-03
- removed .well-known from default URI GH #15

### Fixed
- support POST in doh-httpproxy. GH #12


## [0.0.4] - 2018-01-27

### Fixed
- Create new connection on TooManyStreamsError to work around GH decentfox/aioh2#16

### Changes
- ensure only 1 client is initialized at a time.

## [0.0.3] - 2018-01-17

### Fixed
- proxy: handle empty ct parameter

### Changed
- proxies and stub will listen to ::1 by default.
- proxies better handle malformed DNS messages

## [0.0.2] - 2018-01-16
### Added
- Travis CI
- Support multiple query over the same HTTP2 connection.
- started adding some unittests to utils.py
- `dohprxy/httpproxy.py` a HTTP1 proxy to run as a reverse proxy backend.

### Changed
- code refactor between stub and client
- use logging modules instead of rogue prints
- stub and client now use the same StubServerProtocol as the base to perform
  queries.
- proxy: use logging module instead of print
- doc: improved documentation and provide example setups.

### Removed
- dependency on hyper package

### Fixed
- doh-proxy: properly import dohproxy.protocol
- doh-client: properly set entry_point


## 0.0.1 - 2018-01-11
### Added
- Proxy script `dohproxy/proxy.py`
- Stub script `dohproxy/stub.py`
- Test client script `dohproxy/client.py`
- setuptools' setup.py
- doc
- CHANGELOG.md and README.md

[Unreleased]: https://github.com/facebookexperimental/doh-proxy/compare/v0.0.9...HEAD
[0.0.9]: https://github.com/facebookexperimental/doh-proxy/compare/v0.0.8...v0.0.9
[0.0.8]: https://github.com/facebookexperimental/doh-proxy/compare/v0.0.7...v0.0.8
[0.0.7]: https://github.com/facebookexperimental/doh-proxy/compare/v0.0.6...v0.0.7
[0.0.6]: https://github.com/facebookexperimental/doh-proxy/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/facebookexperimental/doh-proxy/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/facebookexperimental/doh-proxy/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/facebookexperimental/doh-proxy/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/facebookexperimental/doh-proxy/compare/v0.0.1...v0.0.2
