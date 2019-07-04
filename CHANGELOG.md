# Changelog

## [Unreleased]

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
